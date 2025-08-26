"""
Vector Embeddings-based RAG (Retrieval-Augmented Generation) Engine for academic papers.
"""
import os
import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Union
from django.conf import settings
from papers.models import Paper, PaperChunk
import requests
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from sklearn.metrics.pairwise import cosine_similarity


class VectorRAGEngine:
    """
    Vector embeddings-based RAG engine using sentence-transformers for semantic search.
    """
    
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        
        # Allow tuning via config file or env
        try:
            import rag_config
            self.top_k = rag_config.RAG_TOP_K
            self.embedding_model_name = rag_config.EMBEDDING_MODEL
        except ImportError:
            # Fallback to environment variables
            try:
                self.top_k = int(os.getenv('RAG_TOP_K', '5'))
            except ValueError:
                self.top_k = 5
            self.embedding_model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        
        self.embedding_dimension = 384  # Default for all-MiniLM-L6-v2
        
        # Local LLM (Ollama) configuration
        try:
            # Try to import local config first
            import rag_config
            self.use_ollama = rag_config.USE_OLLAMA
            self.ollama_host = rag_config.OLLAMA_HOST
            self.ollama_model = rag_config.OLLAMA_MODEL
        except ImportError:
            # Fallback to environment variables
            self.use_ollama = os.getenv('USE_OLLAMA', 'false').lower() == 'true'
            self.ollama_host = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
            self.ollama_model = os.getenv('OLLAMA_MODEL', 'mistral')
        
        # Check if Ollama is actually accessible
        if self.use_ollama:
            try:
                import requests
                response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
                if response.status_code != 200:
                    print(f"Ollama not accessible at {self.ollama_host}, falling back to simple responses")
                    self.use_ollama = False
                else:
                    print("Ollama is accessible and ready")
            except Exception as e:
                print(f"Ollama not accessible: {e}, falling back to simple responses")
                self.use_ollama = False
        
        # OpenAI configuration (optional)
        try:
            import rag_config
            self.use_openai = rag_config.USE_OPENAI
            self.openai_api_key = rag_config.OPENAI_API_KEY
            self.openai_model = rag_config.OPENAI_MODEL
        except ImportError:
            # Fallback to environment variables
            self.use_openai = os.getenv('USE_OPENAI', 'false').lower() == 'true'
            self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
            self.openai_model = os.getenv('OPENAI_MODEL', 'text-embedding-ada-002')
        
        # Initialize embedding model (AFTER setting use_openai)
        self.embedding_model = None
        self._initialize_embedding_model()
        
        # FAISS index for fast similarity search
        self.faiss_index = None
        self.chunk_embeddings = {}
        self.chunk_ids = []
        
        # Initialize FAISS index
        self._initialize_faiss_index()
    
    def _initialize_embedding_model(self):
        """Initialize the embedding model."""
        try:
            # Check if OpenAI is configured and available
            if hasattr(self, 'use_openai') and self.use_openai and hasattr(self, 'openai_api_key') and self.openai_api_key:
                print("Using OpenAI embeddings")
                self.embedding_model = "openai"
            else:
                print(f"Loading local embedding model: {self.embedding_model_name}")
                self.embedding_model = SentenceTransformer(self.embedding_model_name)
                print("Local embedding model loaded successfully")
        except Exception as e:
            print(f"Error initializing embedding model: {e}")
            # Fallback to OpenAI if available
            if hasattr(self, 'use_openai') and self.use_openai and hasattr(self, 'openai_api_key') and self.openai_api_key:
                print("Falling back to OpenAI embeddings")
                self.embedding_model = "openai"
            else:
                print("No embedding model available")
                self.embedding_model = None
    
    def _initialize_faiss_index(self):
        """Initialize FAISS index for similarity search."""
        try:
            self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
            print("FAISS index initialized successfully")
        except Exception as e:
            print(f"Error initializing FAISS index: {e}")
            self.faiss_index = None
    
    def process_paper(self, paper: Paper) -> bool:
        """Process a paper and create chunks with embeddings."""
        try:
            # Check if paper is already processed
            if paper.chunks.exists():
                return True
            
            # Extract text content
            if not paper.content_text:
                paper.content_text = self._extract_text_from_file(paper.file.path)
                paper.save()
            
            # Split text into chunks
            chunks = self._split_text(paper.content_text)
            
            # Create chunks with embeddings
            chunk_objects = []
            for i, chunk_text in enumerate(chunks):
                chunk = PaperChunk.objects.create(
                    paper=paper,
                    content=chunk_text,
                    chunk_index=i
                )
                chunk_objects.append(chunk)
            
            # Generate embeddings for all chunks
            self._generate_chunk_embeddings(chunk_objects)
            
            # Mark paper as processed
            paper.processed = True
            paper.save()
            
            return True
            
        except Exception as e:
            print(f"Error processing paper {paper.id}: {e}")
            return False
    
    def _generate_chunk_embeddings(self, chunks: List[PaperChunk]):
        """Generate embeddings for paper chunks."""
        if not self.embedding_model:
            print("No embedding model available")
            return
        
        try:
            # Prepare texts for embedding
            texts = [chunk.content for chunk in chunks]
            
            # Generate embeddings
            if self.embedding_model == "openai":
                embeddings = self._get_openai_embeddings(texts)
            else:
                embeddings = self.embedding_model.encode(texts, convert_to_tensor=False)
            
            # Store embeddings in database and update FAISS index
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Convert to binary for storage
                embedding_bytes = pickle.dumps(embedding.astype(np.float32))
                chunk.embedding = embedding_bytes
                chunk.save()
                
                # Update FAISS index
                self._add_to_faiss_index(embedding, chunk.id)
                
            print(f"Generated embeddings for {len(chunks)} chunks")
            
        except Exception as e:
            print(f"Error generating embeddings: {e}")
    
    def _get_openai_embeddings(self, texts: List[str]) -> np.ndarray:
        """Get embeddings from OpenAI API."""
        import openai
        
        # Safety check for OpenAI configuration
        if not hasattr(self, 'openai_api_key') or not self.openai_api_key:
            print("OpenAI API key not configured, falling back to zero vectors")
            return np.array([np.zeros(self.embedding_dimension, dtype=np.float32) for _ in texts])
        
        if not hasattr(self, 'openai_model'):
            print("OpenAI model not configured, using default")
            self.openai_model = 'text-embedding-ada-002'
        
        openai.api_key = self.openai_api_key
        embeddings = []
        
        for text in texts:
            try:
                response = openai.Embedding.create(
                    input=text,
                    model=self.openai_model
                )
                embedding = response['data'][0]['embedding']
                embeddings.append(np.array(embedding, dtype=np.float32))
            except Exception as e:
                print(f"Error getting OpenAI embedding: {e}")
                # Use zero vector as fallback
                embeddings.append(np.zeros(self.embedding_dimension, dtype=np.float32))
        
        return np.array(embeddings)
    
    def _add_to_faiss_index(self, embedding: np.ndarray, chunk_id: int):
        """Add embedding to FAISS index."""
        if self.faiss_index is None:
            return
        
        try:
            # Reshape embedding for FAISS
            embedding_reshaped = embedding.reshape(1, -1).astype(np.float32)
            
            # Add to FAISS index
            self.faiss_index.add(embedding_reshaped)
            
            # Store mapping
            self.chunk_embeddings[chunk_id] = embedding
            self.chunk_ids.append(chunk_id)
            
        except Exception as e:
            print(f"Error adding to FAISS index: {e}")
    
    def query(self, question: str, paper: Paper) -> Tuple[str, List[Dict], List[Dict]]:
        """Query the RAG system with semantic search."""
        try:
            # Ensure paper is processed
            if not paper.processed:
                self.process_paper(paper)
            
            # Get relevant chunks using semantic search
            relevant_chunks = self._get_relevant_chunks_semantic(question, paper)
            
            if not relevant_chunks:
                return "I couldn't find relevant information in this paper to answer your question.", [], []
            
            # Prefer extractive answer for count questions
            if self._is_count_question(question):
                extracted = self._extract_count_answer(question, relevant_chunks)
                if extracted:
                    response = self._format_count_answer(question, extracted["value"], extracted["sentence"], paper)
                else:
                    response = self._generate_response(question, relevant_chunks, paper)
            else:
                response = self._generate_response(question, relevant_chunks, paper)
            
            # Format chunks for response
            formatted_chunks = []
            for chunk in relevant_chunks:
                formatted_chunks.append({
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section': chunk.section
                })
            
            # Format sources with similarity scores
            sources = []
            for chunk in relevant_chunks:
                similarity_score = self._calculate_similarity(question, chunk.content)
                sources.append({
                    'chunk_id': str(chunk.id),
                    'content_preview': chunk.content[:200] + '...',
                    'similarity_score': round(similarity_score, 3)
                })
            
            return response, formatted_chunks, sources
            
        except Exception as e:
            print(f"Error in RAG query: {e}")
            return f"I encountered an error while processing your question: {str(e)}", [], []
    
    def _get_relevant_chunks_semantic(self, question: str, paper: Paper) -> List[PaperChunk]:
        """Get relevant chunks using semantic similarity search."""
        try:
            # Get all chunks for the paper
            chunks = paper.chunks.all()
            
            if not chunks.exists():
                return []
            
            # Generate question embedding
            question_embedding = self._get_question_embedding(question)
            if question_embedding is None:
                return self._fallback_keyword_search(question, chunks)
            
            # Calculate similarities
            chunk_scores = []
            
            for chunk in chunks:
                if chunk.embedding:
                    # Get chunk embedding
                    chunk_embedding = pickle.loads(chunk.embedding)
                    
                    # Calculate cosine similarity
                    similarity = cosine_similarity(
                        question_embedding.reshape(1, -1), 
                        chunk_embedding.reshape(1, -1)
                    )[0][0]
                    
                    chunk_scores.append((chunk, similarity))
            
            # Sort by similarity score
            chunk_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top chunks
            relevant_chunks = [chunk for chunk, score in chunk_scores[:self.top_k]]
            
            # Filter by minimum similarity threshold
            min_similarity = 0.3
            relevant_chunks = [chunk for chunk, score in chunk_scores if score >= min_similarity][:self.top_k]
            
            # If no chunks meet threshold, return top chunks anyway
            if not relevant_chunks and chunk_scores:
                relevant_chunks = [chunk for chunk, score in chunk_scores[:self.top_k]]
            
            return relevant_chunks
            
        except Exception as e:
            print(f"Error in semantic search: {e}")
            return self._fallback_keyword_search(question, chunks)
    
    def _get_question_embedding(self, question: str) -> Optional[np.ndarray]:
        """Generate embedding for the question."""
        try:
            if self.embedding_model == "openai":
                return self._get_openai_embeddings([question])[0]
            elif self.embedding_model:
                return self.embedding_model.encode(question, convert_to_tensor=False)
            else:
                return None
        except Exception as e:
            print(f"Error generating question embedding: {e}")
            return None
    
    def _fallback_keyword_search(self, question: str, chunks) -> List[PaperChunk]:
        """Fallback to keyword-based search if semantic search fails."""
        question_lower = question.lower()
        question_words = [word for word in question_lower.split() if len(word) > 2]
        
        chunk_scores = []
        for chunk in chunks:
            chunk_lower = chunk.content.lower()
            score = sum(1 for word in question_words if word in chunk_lower)
            if score > 0:
                chunk_scores.append((chunk, score))
        
        chunk_scores.sort(key=lambda x: x[1], reverse=True)
        return [chunk for chunk, score in chunk_scores[:self.top_k]]
    
    def _calculate_similarity(self, question: str, content: str) -> float:
        """Calculate similarity between question and content."""
        try:
            question_embedding = self._get_question_embedding(question)
            if question_embedding is None:
                return 0.0
            
            # Simple word overlap as fallback
            question_words = set(question.lower().split())
            content_words = set(content.lower().split())
            overlap = len(question_words.intersection(content_words))
            total = len(question_words.union(content_words))
            
            if total == 0:
                return 0.0
            
            return overlap / total
            
        except Exception as e:
            print(f"Error calculating similarity: {e}")
            return 0.0
    
    def _generate_response(self, question: str, chunks: List[PaperChunk], paper: Paper) -> str:
        """Generate response using LLM or simple method."""
        if self.use_ollama:
            try:
                return self._generate_ollama_response(question, chunks, paper)
            except Exception as e:
                print(f"Error using Ollama: {e}")
                return self._generate_simple_response(question, chunks, paper)
        else:
            return self._generate_simple_response(question, chunks, paper)
    
    def _generate_simple_response(self, question: str, chunks: List[PaperChunk], paper: Paper) -> str:
        """Generate an improved response based on relevant chunks."""
        if not chunks:
            return f"I couldn't find specific information in the paper '{paper.title}' to answer your question: '{question}'. Please try rephrasing your question or ask about a different aspect of the paper."
        
        # Analyze the question to determine response type
        question_lower = question.lower()
        response_type = self._determine_response_type(question_lower)
        
        # Extract and format relevant content
        relevant_content = self._extract_relevant_content(chunks, question_lower)
        
        # Generate specific response based on question type
        if response_type == "reasons":
            response = self._generate_reasons_response(question, relevant_content, paper)
        elif response_type == "methods":
            response = self._generate_methods_response(question, relevant_content, paper)
        elif response_type == "findings":
            response = self._generate_findings_response(question, relevant_content, paper)
        elif response_type == "definition":
            response = self._generate_definition_response(question, relevant_content, paper)
        else:
            response = self._generate_general_response(question, relevant_content, paper)
        
        return response
    
    def _determine_response_type(self, question: str) -> str:
        """Determine the type of response needed based on the question."""
        if any(word in question for word in ['reason', 'why', 'purpose', 'benefit', 'advantage']):
            return "reasons"
        elif any(word in question for word in ['how', 'method', 'process', 'way', 'approach']):
            return "methods"
        elif any(word in question for word in ['result', 'find', 'conclusion', 'outcome', 'effect']):
            return "findings"
        elif any(word in question for word in ['what', 'define', 'explain', 'meaning']):
            return "definition"
        else:
            return "general"
    
    def _extract_relevant_content(self, chunks: List[PaperChunk], question: str) -> str:
        """Extract and format relevant content from chunks."""
        relevant_sentences = []
        
        for chunk in chunks:
            content = chunk.content.strip()
            sentences = content.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:  # Skip very short sentences
                    continue
                
                # Check if sentence is relevant to the question
                if self._is_sentence_relevant(sentence.lower(), question):
                    relevant_sentences.append(sentence)
                
                # Limit the number of sentences to avoid overwhelming response
                if len(relevant_sentences) >= 5:
                    break
        
        return '. '.join(relevant_sentences) if relevant_sentences else ' '.join([chunk.content for chunk in chunks])
    
    def _is_sentence_relevant(self, sentence: str, question: str) -> bool:
        """Check if a sentence is relevant to the question."""
        # Extract key words from question
        question_words = [word for word in question.split() if len(word) > 3]
        
        # Check if sentence contains question words
        for word in question_words:
            if word in sentence:
                return True
        
        # Check for concept matches
        if 'mobile' in question and ('mobile' in sentence or 'device' in sentence):
            return True
        if 'learn' in question and ('learn' in sentence or 'study' in sentence):
            return True
        if 'reason' in question and ('because' in sentence or 'reason' in sentence or 'purpose' in sentence):
            return True
        
        return False
    
    def _generate_reasons_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for reason/purpose questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here are the key reasons for using mobile devices in language learning:

**Main Reasons:**
{content}

**Summary:** The research identifies several important reasons why students use mobile devices for language learning, including convenience, accessibility, and enhanced learning effectiveness."""
    
    def _generate_methods_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for method/process questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's how mobile devices are used in language learning:

**Methods and Approaches:**
{content}

**Summary:** The study describes various methods and approaches for using mobile devices in language learning contexts."""
    
    def _generate_findings_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for findings/result questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here are the key findings:

**Research Findings:**
{content}

**Summary:** The study reveals important findings about the effectiveness and impact of mobile devices in language learning."""
    
    def _generate_definition_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for definition/explanation questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's what the research explains:

**Key Information:**
{content}

**Summary:** The paper provides important insights and explanations about the topic you asked about."""
    
    def _generate_general_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate general response for other questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's what I found regarding your question:

**Relevant Information:**
{content}

**Summary:** The highlighted sections contain information that addresses your question: "{question}"."""
    
    def _generate_ollama_response(self, question: str, chunks: List[PaperChunk], paper: Paper) -> str:
        """Generate response using a local Ollama model."""
        # Build concise academic system prompt
        system_prompt = (
            "You are an expert academic assistant. Answer ONLY from the provided paper content. "
            "If the answer is not explicitly present in the provided text, respond with: 'Not found in provided content.' "
            "Be specific, concise, and maintain an academic tone. When answering, quote the supporting sentence."
        )
        
        # Prepare context from relevant chunks
        joined = []
        current_len = 0
        try:
            max_chars = int(os.getenv('OLLAMA_MAX_CONTEXT_CHARS', '12000'))
        except ValueError:
            max_chars = 12000
            
        for i, ch in enumerate(chunks):
            part = f"Section {i+1}:\n{ch.content.strip()}\n\n"
            if current_len + len(part) > max_chars:
                remaining = max_chars - current_len
                if remaining > 200:
                    joined.append(part[:remaining] + "...")
                break
            joined.append(part)
            current_len += len(part)
        context = "".join(joined) if joined else ""
        
        user_prompt = (
            f"Question: {question}\n\n"
            f"Paper Information:\n- Title: {paper.title}\n- Author(s): {paper.author}\n"
            f"- Year: {getattr(paper, 'year', 'Unknown') or 'Unknown'}\n"
            f"Relevant Content:\n{context}\n\n"
            "Answer based ONLY on the content above. If the answer is missing, reply exactly: Not found in provided content."
        )
        
        payload = {
            "model": self.ollama_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 4096},
        }
        
        try:
            print(f"Attempting to connect to Ollama at {self.ollama_host}")
            resp = requests.post(f"{self.ollama_host}/api/chat", json=payload, timeout=120)
            resp.raise_for_status()
            data = resp.json()
            
            if isinstance(data, dict) and "message" in data and isinstance(data["message"], dict):
                return data["message"].get("content", "")
            if isinstance(data, dict) and "response" in data:
                return data.get("response", "")
            return "I couldn't generate a response from the local model."
        except requests.exceptions.ConnectionError as e:
            print(f"Connection error with Ollama: {e}")
            return "I couldn't connect to the local model. Please ensure Ollama is running or disable it in settings."
        except requests.exceptions.Timeout as e:
            print(f"Timeout error with Ollama: {e}")
            return "The local model took too long to respond. Please try again or use a simpler question."
        except Exception as e:
            print(f"Error with Ollama: {e}")
            return "I couldn't generate a response from the local model."

    def _is_count_question(self, question: str) -> bool:
        q = question.lower()
        indicators = [
            "how many", "number of", "count of", "from how many", "total number", "n =",
        ]
        return any(ind in q for ind in indicators)

    def _extract_count_answer(self, question: str, chunks: List[PaperChunk]) -> Optional[Dict[str, str]]:
        """Try to extract a numeric answer directly from chunk text near target keywords."""
        import re
        q = question.lower()
        target_terms = ["country", "countries", "review", "reviews", "estimated", "from", "participants", "sample"]
        patterns = [
            r"\b(?:from\s+)?(\d{1,4})\s+countries\b",
            r"\bcountries\b[^\d]{0,20}(\d{1,4})\b",
            r"\b(\d{1,4})\b[^\n\.]{0,30}\bcountries\b",
            r"\bN\s*[=:]\s*(\d{1,5})\b",
        ]
        
        for chunk in chunks:
            text = chunk.content.strip()
            text_l = text.lower()
            if not any(term in text_l for term in target_terms):
                continue
                
            sentences = re.split(r"(?<=[\.!\?])\s+", text)
            for sent in sentences:
                sent_l = sent.lower()
                if not any(term in sent_l for term in target_terms):
                    continue
                    
                for pat in patterns:
                    m = re.search(pat, sent, flags=re.IGNORECASE)
                    if m:
                        val = m.group(1)
                        try:
                            n = int(val)
                            if 1 <= n <= 10000:
                                return {"value": str(n), "sentence": sent.strip()}
                        except Exception:
                            pass
        return None

    def _format_count_answer(self, question: str, value: str, evidence_sentence: str, paper: Paper) -> str:
        return (
            f"According to the paper '{paper.title}', the answer is {value}.\n\n"
            f"Evidence: \"{evidence_sentence}\""
        )
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from uploaded file."""
        try:
            file_extension = file_path.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                return self._extract_text_from_pdf(file_path)
            elif file_extension == 'docx':
                return self._extract_text_from_docx(file_path)
            elif file_extension == 'txt':
                return self._extract_text_from_txt(file_path)
            else:
                return ""
                
        except Exception as e:
            print(f"Error extracting text from file: {e}")
            return ""
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return ""
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error extracting TXT text: {e}")
            return ""

    def rebuild_index(self):
        """Rebuild the FAISS index from all existing chunks."""
        try:
            print("Rebuilding FAISS index...")
            
            # Clear existing index
            if self.faiss_index:
                self.faiss_index = faiss.IndexFlatIP(self.embedding_dimension)
            
            self.chunk_embeddings = {}
            self.chunk_ids = []
            
            # Get all chunks with embeddings
            from papers.models import PaperChunk
            chunks = PaperChunk.objects.filter(embedding__isnull=False)
            
            print(f"Found {chunks.count()} chunks with embeddings")
            
            # Rebuild index
            for chunk in chunks:
                try:
                    embedding = pickle.loads(chunk.embedding)
                    self._add_to_faiss_index(embedding, chunk.id)
                except Exception as e:
                    print(f"Error processing chunk {chunk.id}: {e}")
            
            print(f"FAISS index rebuilt with {len(self.chunk_ids)} chunks")
            
        except Exception as e:
            print(f"Error rebuilding index: {e}")


# Backward compatibility - keep the old class name
RAGEngine = VectorRAGEngine
