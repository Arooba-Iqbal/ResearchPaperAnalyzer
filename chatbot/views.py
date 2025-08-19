"""
API views for the chatbot app.
"""
import json
import time
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from papers.models import Paper, PaperChunk
from .models import Conversation, Message, RAGQuery, PaperHighlight
from .serializers import (
    ConversationSerializer, 
    MessageSerializer, 
    RAGQuerySerializer,
    PaperHighlightSerializer
)
from .rag_engine import RAGEngine


class ConversationListView(generics.ListCreateAPIView):
    """List and create conversations."""
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        paper_id = self.request.query_params.get('paper_id')
        if paper_id:
            return Conversation.objects.filter(paper_id=paper_id)
        return Conversation.objects.all()


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a conversation."""
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer


class MessageListView(generics.ListCreateAPIView):
    """List and create messages for a conversation."""
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs['pk']
        return Message.objects.filter(conversation_id=conversation_id)


class ChatView(generics.GenericAPIView):
    """Handle chat interactions."""
    parser_classes = [JSONParser]
    
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        user_message = request.data.get('message', '')
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=user_message
        )
        
        # Process with RAG engine
        rag_engine = RAGEngine()
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(
                user_message, 
                conversation.paper
            )
            processing_time = time.time() - start_time
            
            # Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                message_type='assistant',
                content=response,
                relevant_chunks=relevant_chunks,
                sources=sources
            )
            
            # Create RAG query record
            RAGQuery.objects.create(
                conversation=conversation,
                query=user_message,
                response=response,
                relevant_chunks=relevant_chunks,
                similarity_scores=sources,
                processing_time=processing_time
            )
            
            # Update conversation timestamp
            conversation.save()  # This triggers updated_at update
            
            return Response({
                'user_message': MessageSerializer(user_msg).data,
                'assistant_message': MessageSerializer(assistant_msg).data,
                'processing_time': processing_time
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaperChatView(generics.GenericAPIView):
    """Handle chat interactions for a specific paper."""
    parser_classes = [JSONParser]
    
    def post(self, request, paper_id):
        paper = get_object_or_404(Paper, pk=paper_id)
        user_message = request.data.get('message', '')
        session_id = request.data.get('session_id', '')
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            paper=paper,
            session_id=session_id,
            defaults={'user': request.user if request.user.is_authenticated else None}
        )
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=user_message
        )
        
        # Process with RAG engine
        rag_engine = RAGEngine()
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(user_message, paper)
            processing_time = time.time() - start_time
            
            # Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                message_type='assistant',
                content=response,
                relevant_chunks=relevant_chunks,
                sources=sources
            )
            
            # Prepare highlighting data for frontend (use answer to find exact evidence)
            highlighting_data = self._prepare_highlighting_data(relevant_chunks, answer_text=response)
            
            # Create highlights for relevant content (store best phrases if available)
            self._create_highlights(paper, user_message, response, highlighting_data)
            
            return Response({
                'conversation_id': str(conversation.id),
                'user_message': MessageSerializer(user_msg).data,
                'assistant_message': MessageSerializer(assistant_msg).data,
                'processing_time': processing_time,
                'highlights_created': True,
                'highlighting_data': highlighting_data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_highlights(self, paper, question, answer, highlighting_data_or_chunks):
        """Create highlights for relevant content in the paper."""
        try:
            # Create highlight for the question
            PaperHighlight.objects.create(
                paper=paper,
                message=Message.objects.filter(conversation__paper=paper).last(),
                text_content=question,
                highlight_type='question',
                color='#FF6B6B'
            )
            
            # Create highlight for the answer
            PaperHighlight.objects.create(
                paper=paper,
                message=Message.objects.filter(conversation__paper=paper).last(),
                text_content=answer,
                highlight_type='answer',
                color='#4ECDC4'
            )
            
            # Create highlights for the most relevant phrases (prefer evidence phrases)
            for item in highlighting_data_or_chunks:
                snippet = None
                if isinstance(item, dict):
                    # prefer the first phrase if available
                    phrases = item.get('phrases') or []
                    if phrases:
                        snippet = phrases[0]
                    elif 'content' in item:
                        snippet = (item['content'][:200] + '...') if len(item['content']) > 200 else item['content']
                if snippet:
                    PaperHighlight.objects.create(
                        paper=paper,
                        message=Message.objects.filter(conversation__paper=paper).last(),
                        text_content=snippet,
                        highlight_type='relevant',
                        color='#FFD700'
                    )
        except Exception as e:
            # Log error but don't fail the chat
            print(f"Error creating highlights: {e}")
    
    def _prepare_highlighting_data(self, relevant_chunks, answer_text=None):
        """Prepare highlighting data for frontend with improved highlighting.
        If answer_text is provided, try to locate exact evidence sentences in chunks.
        """
        highlighting_data = []
        
        for chunk in relevant_chunks:
            if 'content' in chunk:
                content = chunk['content']
                phrases = []
                
                # 1) If we have an answer, try to find exact evidence sentences
                if answer_text:
                    phrases = self._extract_evidence_phrases_from_answer(content, answer_text)
                
                # 2) Fallback to general phrase extraction
                if not phrases:
                    phrases = self._extract_highlight_phrases(content)
                
                highlighting_data.append({
                    'chunk_id': chunk.get('id', ''),
                    'content': content,
                    'phrases': phrases,
                    'relevance_score': chunk.get('relevance_score', 0.8),
                    'full_content': content  # Include full content for better highlighting
                })
        
        return highlighting_data
    
    def _extract_highlight_phrases(self, content):
        """Extract meaningful phrases for highlighting from content."""
        import re
        
        # Split into sentences first
        sentences = re.split(r'[.!?]+', content)
        phrases = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30:  # Skip very short sentences
                continue
            
            # Look for the most meaningful parts of the sentence
            # Focus on longer, more complete phrases
            words = sentence.split()
            
            # Extract complete sentences or meaningful clauses
            if len(words) >= 8:
                # Take the full sentence if it's meaningful
                if len(sentence) < 150:  # Not too long
                    phrases.append(sentence)
                else:
                    # Split long sentences into meaningful parts
                    # Look for natural break points (commas, semicolons)
                    parts = re.split(r'[,;]', sentence)
                    for part in parts:
                        part = part.strip()
                        if 20 < len(part) < 120:  # Reasonable length
                            phrases.append(part)
            else:
                # For shorter sentences, use the whole thing if meaningful
                if 20 < len(sentence) < 100:
                    phrases.append(sentence)
            
            # Limit phrases per sentence to avoid overwhelming
            if len(phrases) >= 3:
                break
        
        # If we didn't get enough phrases, add some key content
        if len(phrases) < 2:
            # Extract key content around important words
            important_words = ['study', 'research', 'found', 'shows', 'demonstrates', 'concludes', 'results', 'method', 'approach']
            for word in important_words:
                if word.lower() in content.lower():
                    # Find context around this word
                    word_index = content.lower().find(word.lower())
                    start = max(0, word_index - 50)
                    end = min(len(content), word_index + len(word) + 50)
                    context = content[start:end].strip()
                    if 30 < len(context) < 150:
                        phrases.append(context)
                        break
        
        # Return unique phrases, sorted by relevance (longer phrases first)
        unique_phrases = list(set(phrases))
        return sorted(unique_phrases, key=len, reverse=True)[:5]

    def _extract_evidence_phrases_from_answer(self, content, answer_text):
        """Try to pull exact sentences from content that match numbers/keywords in the answer."""
        import re
        phrases = []
        # Collect numeric tokens and key terms from the answer
        nums = re.findall(r"\b\d{1,6}\b", answer_text)
        key_terms = [
            'countries', 'country', 'participants', 'reviews', 'estimated', 'samples', 'respondents', 'papers', 'studies', 'subjects', 'n =', 'n=' , 'total'
        ]
        sentences = re.split(r'[.!?]+', content)
        for sent in sentences:
            sent_s = sent.strip()
            if len(sent_s) < 20:
                continue
            sent_l = sent_s.lower()
            # sentence should contain at least one number from answer and one key term
            if any(n in sent_s for n in nums) and any(k in sent_l for k in key_terms):
                phrases.append(sent_s)
                if len(phrases) >= 3:
                    break
        return phrases


class PaperHighlightsView(generics.ListAPIView):
    """List highlights for a specific paper."""
    serializer_class = PaperHighlightSerializer
    
    def get_queryset(self):
        paper_id = self.kwargs['paper_id']
        return PaperHighlight.objects.filter(paper_id=paper_id)


class RAGQueryView(generics.GenericAPIView):
    """Direct RAG query endpoint."""
    parser_classes = [JSONParser]
    
    def post(self, request):
        paper_id = request.data.get('paper_id')
        query = request.data.get('query', '')
        
        if not paper_id or not query:
            return Response(
                {'error': 'Both paper_id and query are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paper = get_object_or_404(Paper, pk=paper_id)
        rag_engine = RAGEngine()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(query, paper)
            
            return Response({
                'query': query,
                'response': response,
                'relevant_chunks': relevant_chunks,
                'sources': sources
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
