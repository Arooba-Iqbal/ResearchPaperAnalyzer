"""
Management command to test the reference graph functionality.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from papers.reference_graph_builder import build_reference_graph_for_paper


class Command(BaseCommand):
    help = 'Test the reference graph functionality for a specific paper'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            required=True,
            help='ID of the paper to build reference graph for'
        )
        parser.add_argument(
            '--max-depth',
            type=int,
            default=2,
            help='Maximum depth for the reference graph (default: 2)'
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        max_depth = options['max_depth']
        
        try:
            paper = Paper.objects.get(id=paper_id)
            self.stdout.write(f"Building reference graph for: {paper.title}")
            self.stdout.write(f"Max depth: {max_depth}")
            self.stdout.write("=" * 60)
            
            # Build the reference graph
            graph_data = build_reference_graph_for_paper(paper_id, max_depth=max_depth)
            
            if 'error' in graph_data:
                self.stdout.write(self.style.ERROR(f"Error: {graph_data['error']}"))
                return
            
            # Display results
            self.stdout.write(f"Graph built successfully!")
            self.stdout.write(f"Nodes: {len(graph_data['nodes'])}")
            self.stdout.write(f"Edges: {len(graph_data['edges'])}")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("NODES:")
            self.stdout.write("=" * 60)
            
            for node in graph_data['nodes']:
                status = "✅" if node['has_content'] else "❌"
                self.stdout.write(
                    f"{status} {node['group'].upper()} (Level {node['level']}): {node['title'][:60]}..."
                )
                self.stdout.write(f"     ID: {node['id']}")
                self.stdout.write(f"     Author: {node['author']}")
                self.stdout.write(f"     Content: {'Available' if node['has_content'] else 'Not Available'}")
                self.stdout.write(f"     Chunks: {node['chunks_count']}, Embeddings: {node['embeddings_count']}")
                self.stdout.write("")
            
            self.stdout.write("=" * 60)
            self.stdout.write("EDGES:")
            self.stdout.write("=" * 60)
            
            for edge in graph_data['edges']:
                self.stdout.write(f"From: {edge['from']} → To: {edge['to']}")
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("SUMMARY:")
            self.stdout.write("=" * 60)
            
            # Count by level
            level_counts = {}
            for node in graph_data['nodes']:
                level = node['level']
                if level not in level_counts:
                    level_counts[level] = 0
                level_counts[level] += 1
            
            for level in sorted(level_counts.keys()):
                level_name = "Root" if level == 0 else "Children" if level == 1 else "Grandchildren"
                self.stdout.write(f"Level {level} ({level_name}): {level_counts[level]} papers")
            
            # Count by content availability
            with_content = sum(1 for node in graph_data['nodes'] if node['has_content'])
            without_content = len(graph_data['nodes']) - with_content
            
            self.stdout.write(f"\nPapers with content: {with_content}")
            self.stdout.write(f"Papers without content: {without_content}")
            
            self.stdout.write("\n🎉 Reference graph test completed successfully!")
            
        except Paper.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Paper with ID {paper_id} not found"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            import traceback
            traceback.print_exc()
