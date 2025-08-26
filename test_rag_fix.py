#!/usr/bin/env python3
"""
Quick test to verify the RAG engine initialization fix.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')
django.setup()

def test_rag_initialization():
    """Test if the RAG engine can be initialized without errors."""
    print("Testing RAG Engine Initialization...")
    
    try:
        from chatbot.rag_engine import VectorRAGEngine
        
        print("✅ Successfully imported VectorRAGEngine")
        
        # Try to create an instance
        rag_engine = VectorRAGEngine()
        print("✅ Successfully created VectorRAGEngine instance")
        
        # Check if attributes are properly set
        print(f"   use_openai: {rag_engine.use_openai}")
        print(f"   embedding_model_name: {rag_engine.embedding_model_name}")
        print(f"   embedding_model: {type(rag_engine.embedding_model)}")
        print(f"   faiss_index: {rag_engine.faiss_index is not None}")
        
        # Test if we can access the attributes without errors
        if hasattr(rag_engine, 'use_openai'):
            print("✅ use_openai attribute exists")
        else:
            print("❌ use_openai attribute missing")
            
        if hasattr(rag_engine, 'openai_api_key'):
            print("✅ openai_api_key attribute exists")
        else:
            print("❌ openai_api_key attribute missing")
        
        print("\n🎉 RAG Engine initialization test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ RAG Engine initialization test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_rag_initialization()
    if success:
        print("\n✅ The fix worked! You can now process papers.")
    else:
        print("\n❌ There are still issues. Check the error above.")
