"""
API views for the papers app.
"""
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Paper, Reference, PaperChunk
from .serializers import (
    PaperSerializer, 
    ReferenceSerializer, 
    PaperChunkSerializer,
    PaperUploadSerializer
)
from .utils import extract_references_from_paper


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
