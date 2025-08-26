#!/usr/bin/env python3
"""
Test script for the Vector RAG Engine.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')
django.setup()

from papers.models import Paper, PaperChunk
from chatbot.rag_engine import VectorRAGEngine


def test_vector_rag():
    """Test the vector RAG engine."""
    print("Testing Vector RAG Engine...")
    
    # Initialize RAG engine
    rag_engine = VectorRAGEngine()
    
    # Check if embedding model is available
    if rag_engine.embedding_model is None:
        print("❌ No embedding model available")
        return False
    
    print(f"✅ Embedding model: {rag_engine.embedding_model_name}")
    
    # Check if FAISS index is available
    if rag_engine.faiss_index is None:
        print("❌ FAISS index not available")
        return False
    
    print("✅ FAISS index initialized")
    
    # Test with a sample paper if available
    papers = Paper.objects.all()
    if not papers.exists():
        print("❌ No papers found in database")
        return False
    
    paper = papers.first()
    print(f"✅ Testing with paper: {paper.title}")
    
    # Test question
    test_question = "What are the main findings of this research?"
    print(f"🔍 Testing question: {test_question}")
    
    try:
        response, chunks, sources = rag_engine.query(test_question, paper)
        print(f"✅ Response generated: {response[:100]}...")
        print(f"✅ Found {len(chunks)} relevant chunks")
        print(f"✅ Generated {len(sources)} sources")
        
        # Show similarity scores
        for i, source in enumerate(sources):
            print(f"  Source {i+1}: Score {source['similarity_score']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during query: {e}")
        return False


def test_embedding_generation():
    """Test embedding generation for a paper."""
    print("\nTesting embedding generation...")
    
    rag_engine = VectorRAGEngine()
    
    # Get a paper
    papers = Paper.objects.all()
    if not papers.exists():
        print("❌ No papers found")
        return False
    
    paper = papers.first()
    
    # Check if paper has chunks with embeddings
    chunks = paper.chunks.all()
    if not chunks.exists():
        print(f"❌ Paper '{paper.title}' has no chunks")
        return False
    
    chunks_with_embeddings = chunks.filter(embedding__isnull=False)
    print(f"✅ Paper has {chunks.count()} chunks, {chunks_with_embeddings.count()} with embeddings")
    
    if chunks_with_embeddings.exists():
        # Test similarity calculation
        chunk = chunks_with_embeddings.first()
        question = "What is this research about?"
        
        try:
            similarity = rag_engine._calculate_similarity(question, chunk.content)
            print(f"✅ Similarity calculation: {similarity:.3f}")
            return True
        except Exception as e:
            print(f"❌ Error calculating similarity: {e}")
            return False
    else:
        print("❌ No chunks with embeddings found")
        return False


def main():
    """Main test function."""
    print("=" * 50)
    print("Vector RAG Engine Test Suite")
    print("=" * 50)
    
    # Test basic functionality
    basic_test = test_vector_rag()
    
    # Test embedding generation
    embedding_test = test_embedding_generation()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"Basic RAG functionality: {'✅ PASS' if basic_test else '❌ FAIL'}")
    print(f"Embedding generation: {'✅ PASS' if embedding_test else '❌ FAIL'}")
    
    if basic_test and embedding_test:
        print("\n🎉 All tests passed! Vector RAG engine is working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
    
    print("=" * 50)


if __name__ == "__main__":
    main()
