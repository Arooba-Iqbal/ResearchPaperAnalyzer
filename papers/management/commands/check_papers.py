"""
Management command to check the status of all papers.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper, PaperChunk


class Command(BaseCommand):
    help = 'Check the status of all papers in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='Check a specific paper ID only'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information for each paper'
        )

    def handle(self, *args, **options):
        if options['paper_id']:
            # Check specific paper
            try:
                paper = Paper.objects.get(id=options['paper_id'])
                self._check_paper(paper, detailed=True)
            except Paper.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Paper with ID {options['paper_id']} not found"))
                return
        else:
            # Check all papers
            papers = Paper.objects.all()
            self.stdout.write(f"Found {papers.count()} papers in database")
            
            if papers.count() == 0:
                self.stdout.write("No papers found in database.")
                return
            
            # Summary statistics
            total_papers = papers.count()
            papers_with_content = papers.filter(content_text__isnull=False).exclude(content_text='').count()
            papers_processed = papers.filter(processed=True).count()
            papers_with_chunks = papers.filter(chunks__isnull=False).distinct().count()
            papers_with_embeddings = papers.filter(chunks__embedding__isnull=False).distinct().count()
            
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("PAPER STATUS SUMMARY")
            self.stdout.write("=" * 60)
            self.stdout.write(f"Total papers: {total_papers}")
            self.stdout.write(f"Papers with content text: {papers_with_content}")
            self.stdout.write(f"Papers marked as processed: {papers_processed}")
            self.stdout.write(f"Papers with chunks: {papers_with_chunks}")
            self.stdout.write(f"Papers with embeddings: {papers_with_embeddings}")
            
            # Check each paper
            for paper in papers:
                self._check_paper(paper, detailed=options['detailed'])
    
    def _check_paper(self, paper, detailed=False):
        """Check the status of a specific paper."""
        self.stdout.write(f"\n📄 Paper: {paper.title}")
        self.stdout.write(f"   ID: {paper.id}")
        self.stdout.write(f"   Author: {paper.author or 'Unknown'}")
        self.stdout.write(f"   File: {paper.file.name if paper.file else 'No file'}")
        self.stdout.write(f"   File size: {paper.file.size if paper.file else 'N/A'} bytes")
        self.stdout.write(f"   Uploaded: {paper.uploaded_at}")
        self.stdout.write(f"   Processed: {paper.processed}")
        
        # Content status
        if paper.content_text:
            content_length = len(paper.content_text)
            self.stdout.write(f"   Content text: ✅ Yes ({content_length} characters)")
            if content_length < 100:
                self.stdout.write(f"   ⚠️  Content seems very short: '{paper.content_text[:100]}...'")
        else:
            self.stdout.write("   Content text: ❌ No")
        
        # Chunks status
        chunks = paper.chunks.all()
        chunks_count = chunks.count()
        chunks_with_embeddings = chunks.filter(embedding__isnull=False).count()
        
        self.stdout.write(f"   Chunks: {chunks_count}")
        self.stdout.write(f"   Chunks with embeddings: {chunks_with_embeddings}")
        
        if chunks_count > 0:
            if chunks_with_embeddings == 0:
                self.stdout.write("   ⚠️  Chunks exist but no embeddings!")
            elif chunks_with_embeddings < chunks_count:
                self.stdout.write(f"   ⚠️  Only {chunks_with_embeddings}/{chunks_count} chunks have embeddings")
            else:
                self.stdout.write("   ✅ All chunks have embeddings")
        
        # References status
        references_count = paper.references.count()
        cited_by_count = paper.cited_by.count()
        self.stdout.write(f"   References: {references_count}")
        self.stdout.write(f"   Cited by: {cited_by_count}")
        
        # Detailed chunk information
        if detailed and chunks_count > 0:
            self.stdout.write("   📊 Chunk details:")
            for i, chunk in enumerate(chunks[:5]):  # Show first 5 chunks
                chunk_length = len(chunk.content)
                has_embedding = "✅" if chunk.embedding else "❌"
                self.stdout.write(f"     Chunk {i+1}: {chunk_length} chars, Embedding: {has_embedding}")
            
            if chunks_count > 5:
                self.stdout.write(f"     ... and {chunks_count - 5} more chunks")
        
        # Recommendations
        if not paper.content_text:
            self.stdout.write("   🔧 RECOMMENDATION: Paper needs text extraction")
        elif chunks_count == 0:
            self.stdout.write("   🔧 RECOMMENDATION: Paper needs chunking and embedding generation")
        elif chunks_with_embeddings == 0:
            self.stdout.write("   🔧 RECOMMENDATION: Paper needs embedding generation")
        elif chunks_with_embeddings < chunks_count:
            self.stdout.write("   🔧 RECOMMENDATION: Paper needs complete embedding generation")
        else:
            self.stdout.write("   ✅ Paper is ready for use")
        
        # Show sample content if available
        if detailed and paper.content_text and len(paper.content_text) > 100:
            self.stdout.write(f"   📝 Sample content: '{paper.content_text[:200]}...'")
