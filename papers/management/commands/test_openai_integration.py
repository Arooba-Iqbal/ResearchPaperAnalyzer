"""
Management command to test OpenAI integration with the RAG engine.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from chatbot.rag_engine import RAGEngine


class Command(BaseCommand):
    help = 'Test OpenAI integration with RAG engine'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='ID of the paper to test with (optional)',
        )
        parser.add_argument(
            '--question',
            type=str,
            default='What is this paper about?',
            help='Question to ask about the paper',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🧪 Testing OpenAI Integration with RAG Engine'))
        self.stdout.write('-' * 60)
        
        # Initialize RAG engine
        rag_engine = RAGEngine()
        
        # Check OpenAI status
        if rag_engine.use_openai:
            self.stdout.write(self.style.SUCCESS(f'✅ OpenAI integration active (Model: {rag_engine.model})'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  OpenAI integration not active - using simple responses'))
            self.stdout.write('   Reasons could be:')
            self.stdout.write('   - Missing OPENAI_API_KEY in environment')
            self.stdout.write('   - Invalid API key')
            self.stdout.write('   - OpenAI library not installed')
            self.stdout.write('   - Network connectivity issues')
        
        # Get a paper to test with
        paper_id = options['paper_id']
        if paper_id:
            try:
                paper = Paper.objects.get(id=paper_id)
            except Paper.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Paper with ID {paper_id} not found'))
                return
        else:
            # Get the first available paper
            paper = Paper.objects.first()
            if not paper:
                self.stdout.write(self.style.ERROR('❌ No papers found in the database'))
                self.stdout.write('   Upload a paper first using the web interface or management commands')
                return
        
        self.stdout.write(f'\n📄 Testing with paper: {paper.title[:60]}...')
        self.stdout.write(f'👤 Author: {paper.author}')
        self.stdout.write(f'📅 Year: {paper.year or "Unknown"}')
        
        # Ensure paper is processed
        if not paper.processed:
            self.stdout.write('🔄 Processing paper...')
            success = rag_engine.process_paper(paper)
            if not success:
                self.stdout.write(self.style.ERROR('❌ Failed to process paper'))
                return
            self.stdout.write(self.style.SUCCESS('✅ Paper processed successfully'))
        
        # Test the RAG query
        question = options['question']
        self.stdout.write(f'\n❓ Question: {question}')
        self.stdout.write('-' * 40)
        
        try:
            response, chunks, sources = rag_engine.query(question, paper)
            
            self.stdout.write('\n🤖 Response:')
            self.stdout.write(response)
            
            self.stdout.write(f'\n📊 Retrieved {len(chunks)} relevant chunks')
            self.stdout.write(f'📊 Found {len(sources)} sources')
            
            if chunks:
                self.stdout.write('\n📝 Relevant sections used:')
                for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
                    preview = chunk['content'][:100] + '...' if len(chunk['content']) > 100 else chunk['content']
                    self.stdout.write(f'   {i+1}. {preview}')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error during query: {e}'))
            return
        
        self.stdout.write('\n' + '=' * 60)
        
        if rag_engine.use_openai:
            self.stdout.write(self.style.SUCCESS('🎉 OpenAI integration test completed successfully!'))
            self.stdout.write('   The response above was generated using GPT models.')
        else:
            self.stdout.write(self.style.WARNING('⚠️  Test completed with simple responses'))
            self.stdout.write('   To enable OpenAI:')
            self.stdout.write('   1. Set OPENAI_API_KEY environment variable')
            self.stdout.write('   2. Ensure openai library is installed: pip install openai>=1.3.0')
            self.stdout.write('   3. Restart the Django server')
        
        self.stdout.write('\n💡 Try asking more specific questions like:')
        self.stdout.write('   - "What methodology was used in this study?"')
        self.stdout.write('   - "What were the main findings?"')
        self.stdout.write('   - "What are the limitations of this research?"')


