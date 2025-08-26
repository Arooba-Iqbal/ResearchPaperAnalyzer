"""
Management command to rebuild embeddings for all existing papers.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from chatbot.rag_engine import VectorRAGEngine


class Command(BaseCommand):
    help = 'Rebuild embeddings for all existing papers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='Rebuild embeddings for a specific paper ID only'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force rebuild even if embeddings already exist'
        )

    def handle(self, *args, **options):
        rag_engine = VectorRAGEngine()
        
        if options['paper_id']:
            # Process specific paper
            try:
                paper = Paper.objects.get(id=options['paper_id'])
                self.stdout.write(f"Processing paper: {paper.title}")
                self._process_paper(rag_engine, paper, options['force'])
            except Paper.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Paper with ID {options['paper_id']} not found"))
                return
        else:
            # Process all papers
            papers = Paper.objects.all()
            self.stdout.write(f"Found {papers.count()} papers to process")
            
            for paper in papers:
                self.stdout.write(f"Processing paper: {paper.title}")
                self._process_paper(rag_engine, paper, options['force'])
        
        # Rebuild FAISS index
        self.stdout.write("Rebuilding FAISS index...")
        rag_engine.rebuild_index()
        self.stdout.write(self.style.SUCCESS("Embeddings rebuild completed successfully!"))

    def _process_paper(self, rag_engine, paper, force=False):
        """Process a single paper."""
        try:
            if force or not paper.processed:
                # Clear existing chunks if forcing rebuild
                if force and paper.chunks.exists():
                    paper.chunks.all().delete()
                    self.stdout.write(f"  - Cleared existing chunks for {paper.title}")
                
                # Process paper
                success = rag_engine.process_paper(paper)
                if success:
                    chunk_count = paper.chunks.count()
                    self.stdout.write(f"  - Successfully processed {chunk_count} chunks")
                else:
                    self.stdout.write(self.style.WARNING(f"  - Failed to process {paper.title}"))
            else:
                self.stdout.write(f"  - Paper already processed, skipping")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  - Error processing {paper.title}: {e}"))
