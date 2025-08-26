"""
Reference Graph Builder for academic papers.
Builds a hierarchical graph structure from paper references up to depth 2.
"""
import requests
import time
from typing import Dict, List, Optional, Set
from django.db import transaction
from .models import Paper, Reference
from .utils import extract_references_from_paper


class ReferenceGraphBuilder:
    """
    Builds reference graphs by recursively fetching references.
    Limits depth to level 2 to avoid infinite recursion.
    """
    
    def __init__(self, max_depth: int = 2):
        self.max_depth = max_depth
        self.visited_papers: Set[str] = set()
        self.graph_data = {
            'nodes': [],
            'edges': []
        }
        self.node_counter = 0
    
    def build_graph(self, root_paper: Paper) -> Dict:
        """
        Build a reference graph starting from the root paper.
        
        Args:
            root_paper: The paper to start building the graph from
            
        Returns:
            Dictionary containing nodes and edges for visualization
        """
        print(f"Building reference graph for: {root_paper.title}")
        print(f"Paper ID: {root_paper.id}")
        print(f"Paper has content: {bool(root_paper.content_text)}")
        print(f"Paper has file: {bool(root_paper.file)}")
        print(f"Paper processed: {root_paper.processed}")
        print(f"Paper chunks: {root_paper.chunks.count()}")
        
        # Reset graph data
        self.graph_data = {'nodes': [], 'edges': []}
        self.visited_papers = set()
        self.node_counter = 0
        
        # Add root node
        self._add_paper_node(root_paper, level=0, is_root=True)
        
        # Build graph recursively
        self._build_graph_recursive(root_paper, level=0)
        
        print(f"Graph built with {len(self.graph_data['nodes'])} nodes and {len(self.graph_data['edges'])} edges")
        print(f"Final graph data: {self.graph_data}")
        return self.graph_data
    
    def _build_graph_recursive(self, paper: Paper, level: int):
        """
        Recursively build the reference graph.
        
        Args:
            paper: Current paper to process
            level: Current depth level (0 = root, 1 = children, 2 = grandchildren)
        """
        if level >= self.max_depth:
            print(f"Reached max depth {level} for paper: {paper.title}")
            return
        
        # Get references for this paper
        references = paper.references.all()
        print(f"Processing {references.count()} references at level {level} for: {paper.title}")
        
        # Debug: Print all references
        for ref in references:
            print(f"  - Reference: {ref.target_paper.title if ref.target_paper else 'No target paper'}")
        
        if references.count() == 0:
            print(f"  No references found for paper: {paper.title}")
            return
        
        for reference in references:
            target_paper = reference.target_paper
            
            if not target_paper:
                print(f"  Skipping reference with no target paper")
                continue
            
            # Skip if we've already visited this paper
            if str(target_paper.id) in self.visited_papers:
                print(f"  Skipping {target_paper.title} - already visited")
                continue
            
            # Check if target paper has online content
            has_content = self._has_online_content(target_paper)
            print(f"  Target paper {target_paper.title} has content: {has_content}")
            
            # Add ALL references to the graph, regardless of content availability
            # This gives users a complete view of the reference structure
            self._add_paper_node(target_paper, level=level + 1, is_root=False, has_content=has_content)
            
            # Add edge from parent to child
            self._add_edge(paper, target_paper, reference)
            
            # Mark as visited
            self.visited_papers.add(str(target_paper.id))
            
            # Only recursively process if the paper has content (to avoid infinite loops with empty papers)
            if has_content:
                self._build_graph_recursive(target_paper, level + 1)
            else:
                print(f"  Not recursing into {target_paper.title} - no content available")
    
    def _has_online_content(self, paper: Paper) -> bool:
        """
        Check if a paper has accessible online content.
        
        Args:
            paper: Paper to check
            
        Returns:
            True if paper has online content, False otherwise
        """
        # Check if paper has content text
        if paper.content_text and len(paper.content_text.strip()) > 100:
            return True
        
        # Check if paper has a file
        if paper.file:
            return True
        
        # Check if paper has chunks (processed content)
        if paper.chunks.exists():
            return True
        
        # Check if paper has been processed
        if paper.processed:
            return True
        
        return False
    
    def _add_paper_node(self, paper: Paper, level: int, is_root: bool = False, has_content: bool = None):
        """
        Add a paper as a node in the graph.
        
        Args:
            paper: Paper to add as node
            level: Depth level (0 = root, 1 = children, 2 = grandchildren)
            is_root: Whether this is the root node
            has_content: Whether the paper has accessible content (overrides auto-detection)
        """
        # Create safe label by truncating and cleaning the title
        safe_title = paper.title[:50] + '...' if len(paper.title) > 50 else paper.title
        safe_title = safe_title.replace('\n', ' ').replace('\r', ' ').strip()
        
        # Determine node properties based on level and content availability
        if is_root:
            group = 'root'
            color = '#FF6B6B'  # Red for root
            size = 30
        elif level == 1:
            if has_content is None:
                has_content = self._has_online_content(paper)
            
            if has_content:
                group = 'children'
                color = '#4ECDC4'  # Teal for children with content
                size = 25
            else:
                group = 'children_no_content'
                color = '#FFA07A'  # Light orange for children without content
                size = 20
        else:  # level == 2
            if has_content is None:
                has_content = self._has_online_content(paper)
            
            if has_content:
                group = 'grandchildren'
                color = '#45B7D1'  # Blue for grandchildren with content
                size = 20
            else:
                group = 'grandchildren_no_content'
                color = '#DDA0DD'  # Plum for grandchildren without content
                size = 15
        
        node = {
            'id': str(paper.id),
            'label': safe_title,
            'title': paper.title,
            'author': paper.author or 'Unknown Author',
            'group': group,
            'color': color,
            'size': size,
            'level': level,
            'is_root': is_root,
            'paper_id': str(paper.id),
            'has_content': has_content if has_content is not None else self._has_online_content(paper),
            'chunks_count': paper.chunks.count(),
            'embeddings_count': paper.chunks.filter(embedding__isnull=False).count()
        }
        
        self.graph_data['nodes'].append(node)
        self.node_counter += 1
        
        content_status = "with content" if node['has_content'] else "without content"
        print(f"Added node: {safe_title} (Level {level}, Group: {group}, {content_status})")
    
    def _add_edge(self, source_paper: Paper, target_paper: Paper, reference: Reference):
        """
        Add an edge between two papers in the graph.
        
        Args:
            source_paper: Source paper (parent)
            target_paper: Target paper (child)
            reference: Reference object connecting them
        """
        edge = {
            'from': str(source_paper.id),
            'to': str(target_paper.id),
            'arrows': 'to',
            'label': 'references',
            'width': 2,
            'color': '#666666'
        }
        
        self.graph_data['edges'].append(edge)
    
    def get_paper_info(self, paper_id: str) -> Optional[Dict]:
        """
        Get detailed information about a paper for the chatbot.
        
        Args:
            paper_id: ID of the paper
            
        Returns:
            Dictionary with paper information or None if not found
        """
        try:
            paper = Paper.objects.get(id=paper_id)
            return {
                'id': str(paper.id),
                'title': paper.title,
                'author': paper.author,
                'content_text': paper.content_text,
                'has_content': self._has_online_content(paper),
                'chunks_count': paper.chunks.count(),
                'embeddings_count': paper.chunks.filter(embedding__isnull=False).count(),
                'processed': paper.processed,
                'references_count': paper.references.count()
            }
        except Paper.DoesNotExist:
            return None


def build_reference_graph_for_paper(paper_id: str, max_depth: int = 2) -> Dict:
    """
    Convenience function to build a reference graph for a specific paper.
    
    Args:
        paper_id: ID of the paper to build graph for
        max_depth: Maximum depth to build (default: 2)
        
    Returns:
        Dictionary containing graph data (nodes and edges)
    """
    try:
        paper = Paper.objects.get(id=paper_id)
        builder = ReferenceGraphBuilder(max_depth=max_depth)
        return builder.build_graph(paper)
    except Paper.DoesNotExist:
        return {'nodes': [], 'edges': [], 'error': f'Paper with ID {paper_id} not found'}


def get_paper_for_chat(paper_id: str) -> Optional[Dict]:
    """
    Get paper information for chatbot interaction.
    
    Args:
        paper_id: ID of the paper
        
    Returns:
        Dictionary with paper info or None if not found
    """
    try:
        paper = Paper.objects.get(id=paper_id)
        return {
            'id': str(paper.id),
            'title': paper.title,
            'author': paper.author,
            'content_text': paper.content_text,
            'has_content': bool(paper.content_text and len(paper.content_text.strip()) > 100),
            'chunks_count': paper.chunks.count(),
            'embeddings_count': paper.chunks.filter(embedding__isnull=False).count(),
            'processed': paper.processed,
            'can_chat': paper.chunks.filter(embedding__isnull=False).exists()
        }
    except Paper.DoesNotExist:
        return None
