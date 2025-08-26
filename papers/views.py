"""
API views for the papers app.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404, render
from django.db.models import Q
from .models import Paper, Reference, PaperChunk
from .serializers import (
    PaperSerializer, 
    ReferenceSerializer, 
    PaperChunkSerializer,
    PaperUploadSerializer
)
from .utils import extract_references_from_paper
from .reference_graph_builder import build_reference_graph_for_paper, get_paper_for_chat


class PaperListView(generics.ListAPIView):
    """List all papers with optional filtering."""
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    
    def get_queryset(self):
        queryset = Paper.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(author__icontains=search) |
                Q(abstract__icontains=search)
            )
        return queryset


class PaperDetailView(generics.RetrieveAPIView):
    """Retrieve a specific paper."""
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer


class PaperGraphView(generics.RetrieveAPIView):
    """Display interactive reference graph for a paper."""
    queryset = Paper.objects.all()
    serializer_class = PaperSerializer
    template_name = 'reference_graph_interactive.html'
    
    def get(self, request, *args, **kwargs):
        paper = self.get_object()
        
        # Compute status values for the template
        chunks_with_embeddings = paper.chunks.filter(embedding__isnull=False).exists()
        paper_status = 'ready' if (paper.processed and chunks_with_embeddings) else 'processing' if paper.processed else 'error'
        
        context = {
            'paper': paper,
            'paper_status': paper_status,
            'chunks_with_embeddings': chunks_with_embeddings,
            'chunks_count': paper.chunks.count(),
            'embeddings_count': paper.chunks.filter(embedding__isnull=False).count()
        }
        
        return render(request, self.template_name, context)


class PaperReferencesView(generics.ListAPIView):
    """List all references for a specific paper."""
    serializer_class = ReferenceSerializer
    
    def get_queryset(self):
        paper = get_object_or_404(Paper, pk=self.kwargs['pk'])
        return paper.references.all()


class PaperCitedByView(generics.ListAPIView):
    """List all papers that cite a specific paper."""
    serializer_class = PaperSerializer
    
    def get_queryset(self):
        paper = get_object_or_404(Paper, pk=self.kwargs['pk'])
        # Return the papers that cite this paper (source_paper from references)
        return Paper.objects.filter(references__target_paper=paper)


class PaperChunksView(generics.ListAPIView):
    """List all chunks for a specific paper."""
    serializer_class = PaperChunkSerializer
    
    def get_queryset(self):
        paper = get_object_or_404(Paper, pk=self.kwargs['pk'])
        return paper.chunks.all()


class PaperUploadView(generics.CreateAPIView):
    """Upload a new paper."""
    parser_classes = (MultiPartParser, FormParser)
    serializer_class = PaperUploadSerializer
    permission_classes = [IsAuthenticated]
    
    def perform_create(self, serializer):
        paper = serializer.save()
        
        # Extract references synchronously (no recursion on upload)
        extract_references_from_paper(str(paper.id))
        
        # Process paper with RAG engine to generate embeddings and chunks
        try:
            from chatbot.rag_engine import VectorRAGEngine
            rag_engine = VectorRAGEngine()
            success = rag_engine.process_paper(paper)
            if success:
                print(f"Successfully processed paper {paper.id} with RAG engine")
            else:
                print(f"Failed to process paper {paper.id} with RAG engine")
        except Exception as e:
            print(f"Error processing paper {paper.id} with RAG engine: {e}")
            # Don't fail the upload, just log the error


class PaperSearchView(generics.ListAPIView):
    """Search papers by content."""
    serializer_class = PaperSerializer
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return Paper.objects.none()
        
        # Search in title, author, abstract, and content
        return Paper.objects.filter(
            Q(title__icontains=query) |
            Q(author__icontains=query) |
            Q(abstract__icontains=query) |
            Q(content_text__icontains=query)
        )


class GraphDataView(generics.GenericAPIView):
    """Get graph data for visualization."""
    
    def get(self, request):
        try:
            papers = Paper.objects.all()
            nodes = []
            edges = []
            
            for paper in papers:
                try:
                    # Create a safe label by truncating and cleaning the title
                    safe_title = paper.title[:50] + '...' if len(paper.title) > 50 else paper.title
                    safe_title = safe_title.replace('\n', ' ').replace('\r', ' ').replace('\u25fe', '•').strip()
                    
                    nodes.append({
                        'id': str(paper.id),
                        'label': safe_title,
                        'title': paper.title,
                        'author': paper.author or 'Unknown Author',
                        'group': 'paper',
                        'size': 20 + (paper.citation_count * 2)  # Size based on citations
                    })
                    
                    # Add reference edges
                    for ref in paper.references.all():
                        edges.append({
                            'from': str(paper.id),
                            'to': str(ref.target_paper.id),
                            'arrows': 'to',
                            'label': 'references',
                            'width': 2
                        })
                except Exception as e:
                    print(f"Error processing paper {paper.id}: {e}")
                    continue
            
            return Response({
                'nodes': nodes,
                'edges': edges
            })
        except Exception as e:
            print(f"Error in GraphDataView: {e}")
            return Response({
                'error': str(e),
                'nodes': [],
                'edges': []
            }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_paper_references(request, pk):
    """Manually trigger reference extraction for a paper."""
    try:
        print(f"Processing references for paper: {pk}")
        paper = get_object_or_404(Paper, pk=pk)
        print(f"Found paper: {paper.title}")
        
        # Check if paper has content
        if not paper.content_text and not paper.file:
            return Response({
                'error': 'Paper has no content or file to process'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Extract references (no recursion here)
        success = extract_references_from_paper(str(paper.id))

        if success:
            # Refresh paper to get updated reference count
            paper.refresh_from_db()
            return Response({
                'message': 'Reference extraction completed successfully',
                'references_found': paper.references.count()
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Reference extraction failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        print(f"Error in process_paper_references: {e}")
        return Response({
            'error': f'Error processing references: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_paper_rag(request, pk):
    """Manually trigger RAG processing for a paper."""
    try:
        print(f"Processing RAG for paper: {pk}")
        paper = get_object_or_404(Paper, pk=pk)
        print(f"Found paper: {paper.title}")
        
        # Check if paper has content
        if not paper.content_text and not paper.file:
            return Response({
                'error': 'Paper has no content or file to process'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process with RAG engine
        from chatbot.rag_engine import VectorRAGEngine
        rag_engine = VectorRAGEngine()
        success = rag_engine.process_paper(paper)
        
        if success:
            # Refresh paper to get updated chunk count
            paper.refresh_from_db()
            chunk_count = paper.chunks.count()
            chunks_with_embeddings = paper.chunks.filter(embedding__isnull=False).count()
            
            return Response({
                'message': 'RAG processing completed successfully',
                'chunks_created': chunk_count,
                'chunks_with_embeddings': chunks_with_embeddings,
                'paper_processed': paper.processed
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'RAG processing failed'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        print(f"Error in process_paper_rag: {e}")
        return Response({
            'error': f'Error processing RAG: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_reference_graph(request, pk):
    """Get reference graph for a specific paper."""
    try:
        paper = get_object_or_404(Paper, pk=pk)
        
        # Build reference graph
        graph_data = build_reference_graph_for_paper(str(paper.id), max_depth=2)
        
        return Response({
            'paper_id': str(paper.id),
            'paper_title': paper.title,
            'graph': graph_data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error building reference graph: {e}")
        return Response({
            'error': f'Error building reference graph: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_paper_details(request, pk):
    """Get detailed information about a paper for graph interaction."""
    try:
        paper_info = get_paper_for_chat(str(pk))
        
        if not paper_info:
            return Response({
                'error': 'Paper not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response(paper_info, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Error getting paper details: {e}")
        return Response({
            'error': f'Error getting paper details: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
