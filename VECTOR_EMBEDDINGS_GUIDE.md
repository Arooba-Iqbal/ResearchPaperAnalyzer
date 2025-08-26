# Vector Embeddings-Based RAG System Guide

This guide explains how to use the new vector embeddings-based RAG (Retrieval-Augmented Generation) system that replaces the keyword-based approach.

## Overview

The new system uses **semantic similarity** instead of keyword matching to find relevant content. This means:

- **Better understanding**: The system understands the meaning of questions, not just exact word matches
- **Improved accuracy**: More relevant chunks are retrieved for better answers
- **Semantic search**: Questions like "What causes climate change?" will find content about "global warming causes" even without exact word matches

## Key Components

### 1. Embedding Models

The system supports two types of embedding models:

#### Local Embeddings (Default)
- **Model**: `all-MiniLM-L6-v2` (384 dimensions)
- **Advantage**: Free, no API keys needed, works offline
- **Performance**: Good for most academic papers
- **Memory**: ~80MB model size

#### OpenAI Embeddings (Optional)
- **Model**: `text-embedding-ada-002` (1536 dimensions)
- **Advantage**: Higher quality, better semantic understanding
- **Cost**: ~$0.0001 per 1K tokens
- **Requirement**: OpenAI API key

### 2. FAISS Index

- **Purpose**: Fast similarity search across all paper chunks
- **Type**: Inner Product (cosine similarity)
- **Performance**: Sub-second search across thousands of chunks

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

The new requirements include:
- `sentence-transformers`: Local embedding models
- `numpy`: Numerical operations
- `scikit-learn`: Similarity calculations
- `faiss-cpu`: Fast similarity search

### 2. Environment Configuration

Create a `.env` file based on `env.example`:

```bash
# Embedding Model Configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
USE_OPENAI=false
OPENAI_API_KEY=your-key-here  # Only if using OpenAI

# RAG Configuration
RAG_TOP_K=5  # Number of chunks to retrieve

# Ollama Configuration (for response generation)
USE_OLLAMA=false
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral
```

## Usage

### 1. Basic Usage

The system automatically generates embeddings when papers are processed:

```python
from chatbot.rag_engine import VectorRAGEngine

# Initialize the engine
rag_engine = VectorRAGEngine()

# Process a paper (generates embeddings automatically)
paper = Paper.objects.get(id='paper-id')
rag_engine.process_paper(paper)

# Query the system
response, chunks, sources = rag_engine.query("What are the main findings?", paper)
```

### 2. Rebuilding Embeddings

If you have existing papers, rebuild their embeddings:

```bash
# Rebuild all papers
python manage.py rebuild_embeddings

# Rebuild specific paper
python manage.py rebuild_embeddings --paper-id "uuid-here"

# Force rebuild (overwrite existing)
python manage.py rebuild_embeddings --force
```

### 3. Testing the System

Run the test script to verify everything works:

```bash
python test_vector_rag.py
```

## How It Works

### 1. Paper Processing

1. **Text Extraction**: Extract text from PDF/DOCX files
2. **Chunking**: Split into 1000-word chunks with 200-word overlap
3. **Embedding Generation**: Create vector embeddings for each chunk
4. **Storage**: Save embeddings as binary data in database
5. **Indexing**: Add embeddings to FAISS index for fast search

### 2. Query Processing

1. **Question Embedding**: Convert user question to vector
2. **Similarity Search**: Find most similar chunks using FAISS
3. **Chunk Retrieval**: Return top-K most relevant chunks
4. **Response Generation**: Use LLM or simple method to generate answer
5. **Source Attribution**: Provide similarity scores and chunk references

### 3. Similarity Calculation

The system uses **cosine similarity** between question and chunk embeddings:

```
similarity = (A · B) / (||A|| × ||B||)
```

Where A and B are the question and chunk embedding vectors.

## Performance Optimization

### 1. Chunk Size Tuning

Adjust chunk size based on your content:

```python
# In rag_engine.py
self.chunk_size = 1000      # Larger chunks = more context
self.chunk_overlap = 200    # Overlap prevents context loss
```

### 2. Top-K Selection

Balance between relevance and context:

```bash
# Environment variable
RAG_TOP_K=5  # More chunks = more context but potentially less focused
```

### 3. Similarity Threshold

Filter out low-quality matches:

```python
# In _get_relevant_chunks_semantic method
min_similarity = 0.3  # Adjust based on your needs
```

## Troubleshooting

### 1. Common Issues

#### "No embedding model available"
- Check if `sentence-transformers` is installed
- Verify model name in `EMBEDDING_MODEL` environment variable
- Try downloading the model manually: `python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`

#### "FAISS index not available"
- Check if `faiss-cpu` is installed
- Verify embedding dimension matches model (384 for all-MiniLM-L6-v2)

#### "Memory errors during embedding generation"
- Reduce chunk size
- Process papers in batches
- Use smaller embedding model

### 2. Performance Issues

#### Slow embedding generation
- Use GPU if available: `pip install faiss-gpu`
- Consider OpenAI embeddings for faster processing
- Process papers in background tasks

#### Slow similarity search
- Reduce FAISS index size
- Use approximate search: `faiss.IndexIVFFlat` instead of `IndexFlatIP`
- Implement caching for frequent queries

## Advanced Features

### 1. Custom Embedding Models

You can use different sentence-transformers models:

```bash
# Better quality, larger size
EMBEDDING_MODEL=all-mpnet-base-v2

# Faster, smaller size
EMBEDDING_MODEL=paraphrase-MiniLM-L3-v2

# Multilingual support
EMBEDDING_MODEL=paraphrase-multilingual-MiniLM-L12-v2
```

### 2. Hybrid Search

The system falls back to keyword search if semantic search fails:

```python
# Automatic fallback in _get_relevant_chunks_semantic
if question_embedding is None:
    return self._fallback_keyword_search(question, chunks)
```

### 3. Batch Processing

Process multiple papers efficiently:

```python
from django.db import transaction

@transaction.atomic
def process_papers_batch(papers):
    rag_engine = VectorRAGEngine()
    for paper in papers:
        rag_engine.process_paper(paper)
```

## Migration from Keyword-Based System

### 1. Automatic Migration

The new system is backward compatible:
- Existing `RAGEngine` class now points to `VectorRAGEngine`
- Old code continues to work
- Embeddings are generated automatically for new papers

### 2. Data Migration

For existing papers:
```bash
# Rebuild all embeddings
python manage.py rebuild_embeddings

# Or rebuild specific papers
python manage.py rebuild_embeddings --paper-id "uuid"
```

### 3. Code Updates

Update your code to take advantage of new features:

```python
# Old way (still works)
from chatbot.rag_engine import RAGEngine
rag_engine = RAGEngine()

# New way (recommended)
from chatbot.rag_engine import VectorRAGEngine
rag_engine = VectorRAGEngine()

# Access new features
rag_engine.rebuild_index()  # Rebuild FAISS index
```

## Best Practices

### 1. Paper Processing

- Process papers in background tasks for large datasets
- Monitor memory usage during embedding generation
- Implement error handling for failed processing

### 2. Query Optimization

- Use specific, well-formed questions
- Avoid overly broad queries
- Leverage similarity scores for result filtering

### 3. Maintenance

- Regularly rebuild FAISS index after adding papers
- Monitor embedding quality and model performance
- Update embedding models periodically

## Monitoring and Metrics

### 1. Performance Metrics

Track these key indicators:
- Embedding generation time per paper
- Query response time
- Similarity score distribution
- Chunk retrieval accuracy

### 2. Quality Metrics

Monitor:
- User satisfaction with responses
- Relevance of retrieved chunks
- Coverage of paper content

## Future Enhancements

Potential improvements:
- **Hierarchical embeddings**: Document-level + chunk-level
- **Dynamic chunking**: Adaptive chunk sizes based on content
- **Multi-modal embeddings**: Support for figures, tables, equations
- **Incremental indexing**: Add new chunks without rebuilding entire index
- **Query expansion**: Automatically expand user questions for better retrieval

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Run the test script to identify problems
3. Review Django logs for error details
4. Verify environment configuration

---

**Note**: The vector embeddings system provides significant improvements over keyword-based search, but requires more computational resources. Ensure your system has adequate memory and processing power for optimal performance.
