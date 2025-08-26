#!/usr/bin/env python3
"""
Script to process existing papers with the RAG engine.
This is useful for papers that were uploaded before the vector embeddings system was implemented.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')
django.setup()

from papers.models import Paper
from chatbot.rag_engine import VectorRAGEngine


def process_existing_papers():
    """Process all existing papers that don't have embeddings."""
    print("=" * 60)
    print("Processing Existing Papers with RAG Engine")
    print("=" * 60)
    
    # Initialize RAG engine
    try:
        rag_engine = VectorRAGEngine()
        print("✅ RAG engine initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize RAG engine: {e}")
        return False
    
    # Get all papers
    papers = Paper.objects.all()
    print(f"Found {papers.count()} papers in database")
    
    if papers.count() == 0:
        print("No papers found. Please upload some papers first.")
        return True
    
    # Process each paper
    processed_count = 0
    failed_count = 0
    
    for paper in papers:
        print(f"\n📄 Processing paper: {paper.title}")
        print(f"   ID: {paper.id}")
        print(f"   File: {paper.file.name if paper.file else 'No file'}")
        print(f"   Content text: {'Yes' if paper.content_text else 'No'}")
        print(f"   Processed: {paper.processed}")
        print(f"   Chunks: {paper.chunks.count()}")
        
        # Check if paper has chunks with embeddings
        chunks_with_embeddings = paper.chunks.filter(embedding__isnull=False).count()
        print(f"   Chunks with embeddings: {chunks_with_embeddings}")
        
        if chunks_with_embeddings > 0:
            print("   ✅ Paper already has embeddings, skipping...")
            continue
        
        try:
            # Process paper with RAG engine
            success = rag_engine.process_paper(paper)
            
            if success:
                # Refresh paper to get updated information
                paper.refresh_from_db()
                new_chunk_count = paper.chunks.count()
                new_embeddings_count = paper.chunks.filter(embedding__isnull=False).count()
                
                print(f"   ✅ Successfully processed!")
                print(f"   📊 New chunks: {new_chunk_count}")
                print(f"   🔢 New embeddings: {new_embeddings_count}")
                processed_count += 1
            else:
                print(f"   ❌ Failed to process paper")
                failed_count += 1
                
        except Exception as e:
            print(f"   ❌ Error processing paper: {e}")
            failed_count += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("Processing Summary:")
    print(f"Total papers: {papers.count()}")
    print(f"Successfully processed: {processed_count}")
    print(f"Failed: {failed_count}")
    print(f"Skipped (already processed): {papers.count() - processed_count - failed_count}")
    
    if processed_count > 0:
        print("\n🎉 Successfully processed papers! You can now use the chatbot.")
        print("\nNext steps:")
        print("1. Test the chatbot with one of the processed papers")
        print("2. Check that papers show content when viewed")
        print("3. Verify that questions return relevant answers")
    else:
        print("\n⚠️  No papers were processed. Check the error messages above.")
    
    print("=" * 60)
    return processed_count > 0


def check_paper_status():
    """Check the status of all papers."""
    print("\n" + "=" * 60)
    print("Paper Status Check")
    print("=" * 60)
    
    papers = Paper.objects.all()
    
    for paper in papers:
        chunks_count = paper.chunks.count()
        embeddings_count = paper.chunks.filter(embedding__isnull=False).count()
        processed = paper.processed
        
        status = "✅ Ready" if embeddings_count > 0 else "❌ Needs Processing"
        
        print(f"{status} | {paper.title[:50]}...")
        print(f"     Chunks: {chunks_count}, Embeddings: {embeddings_count}, Processed: {processed}")


if __name__ == "__main__":
    try:
        # Process existing papers
        success = process_existing_papers()
        
        # Show status
        check_paper_status()
        
        if success:
            print("\n🎉 All done! Your papers should now work with the chatbot.")
        else:
            print("\n⚠️  Some issues occurred. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Script failed with error: {e}")
        sys.exit(1)
