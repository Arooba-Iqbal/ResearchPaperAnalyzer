# Academic Reference Graph

A comprehensive Django-based academic paper reference graph system with RAG (Retrieval-Augmented Generation) capabilities. This application allows users to upload academic papers, automatically extract references, build interconnected citation networks, and interact with papers through an AI-powered chatbot.

##  Features

### Core Functionality
- **Paper Upload & Processing**: Support for PDF, DOCX, and TXT files
- **Automatic Reference Extraction**: AI-powered extraction of citations and references
- **Reference Graph Visualization**: Interactive network graph showing paper relationships
- **Vector Embeddings RAG**: Advanced semantic search using vector embeddings
- **Content Highlighting**: Automatic highlighting of relevant content based on questions

### Advanced Features
- **Vector Embeddings**: Sentence transformers for semantic similarity search
- **FAISS Index**: Fast similarity search across paper chunks
- **AI-Powered Analysis**: OpenAI integration for intelligent paper understanding
- **Real-time Processing**: Asynchronous processing with Celery and Redis
- **Responsive Design**: Modern, mobile-friendly interface
- **Zoom Functionality**: Enhanced paper viewing with zoom controls

### Technical Features
- **Django REST Framework**: Robust API endpoints
- **Vector Embeddings**: Sentence transformers for semantic search
- **FAISS**: Fast similarity search and indexing
- **Document Chunking**: Intelligent text segmentation for RAG
- **Reference Pattern Recognition**: Advanced regex patterns for citation extraction
- **External API Integration**: CrossRef and arXiv for paper metadata

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Django        │    │   RAG Engine    │
│   (HTML/CSS/JS) │◄──►│   Backend       │◄──►│   (AI/Vector)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   ChromaDB      │
                       │   (Vector DB)   │
                       └─────────────────┘
```

## 🛠️ Technology Stack

- **Backend**: Django 4.2, Django REST Framework
- **Database**: SQLite (default), PostgreSQL (production)
- **Vector Search**: FAISS for fast similarity search
- **AI/ML**: OpenAI GPT, Sentence Transformers, Vector Embeddings
- **Task Queue**: Celery + Redis
- **Frontend**: Bootstrap 5, JavaScript, Vis.js
- **File Processing**: PyPDF2, python-docx

## 📋 Prerequisites

- Python 3.8+
- Redis server
- OpenAI API key
- Virtual environment (recommended)

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd academic-reference-graph
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Environment Configuration
```bash
cp env.example .env
# Edit .env with your configuration
```

Required environment variables:
- `SECRET_KEY`: Django secret key
- `OPENAI_API_KEY`: Your OpenAI API key
- `DEBUG`: Set to True for development

### 5. Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### 6. Start Redis Server
```bash
# On macOS with Homebrew
brew install redis
brew services start redis

# On Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# On Windows, download Redis from https://redis.io/download
```

### 7. Install Vector Embeddings Dependencies
```bash
# Install new dependencies for vector embeddings
python install_vector_deps.py

# Or manually install
pip install sentence-transformers numpy scikit-learn faiss-cpu
```

### 8. Rebuild Embeddings (for existing papers)
```bash
# Rebuild embeddings for all existing papers
python manage.py rebuild_embeddings

# Test the system
python test_vector_rag.py
```

### 9. Run the Application
```bash
# Terminal 1: Django server
python manage.py runserver

# Terminal 2: Celery worker
celery -A reference_graph worker --loglevel=info

# Terminal 3: Celery beat (optional, for scheduled tasks)
celery -A reference_graph beat --loglevel=info
```

## 📖 Usage

### 1. Upload a Paper
- Navigate to `/upload/`
- Fill in paper details (title, author, etc.)
- Upload PDF/DOCX/TXT file
- System automatically processes and extracts references

### 2. View Reference Graph
- Go to `/graph/`
- Interactive visualization of paper relationships
- Click nodes to see paper details
- Zoom, pan, and explore the network

### 3. Interact with Papers
- Click on any paper in the graph
- Use zoom controls for better readability
- Toggle chatbot for AI-powered questions
- Get highlighted relevant content

### 4. Chat with Papers
- Ask questions about methodology, findings, or references
- AI provides context-aware answers using vector embeddings
- Semantic search finds most relevant content automatically
- Relevant content is automatically highlighted
- Conversation history is maintained

### 5. Vector Embeddings Features
- **Semantic Search**: Find content by meaning, not just keywords
- **FAISS Index**: Fast similarity search across all paper chunks
- **Local Models**: Use sentence-transformers without API costs
- **OpenAI Integration**: Optional high-quality embeddings
- **Similarity Scores**: See how relevant each chunk is to your question

## Configuration

### OpenAI API
```python
# settings.py
OPENAI_API_KEY = 'your-api-key'
OPENAI_MODEL = 'gpt-3.5-turbo'  # or 'gpt-4'
```

### ChromaDB
```python
# settings.py
CHROMA_DB_PATH = '/path/to/chroma_db'
```

### File Upload Limits
```python
# settings.py
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50MB
```

## API Endpoints

### Papers
- `GET /api/papers/` - List all papers
- `POST /api/papers/upload/` - Upload new paper
- `GET /api/papers/{id}/` - Get paper details
- `GET /api/papers/{id}/references/` - Get paper references
- `GET /api/papers/graph-data/` - Get graph data

### Chatbot
- `POST /api/chatbot/papers/{id}/chat/` - Chat with paper
- `GET /api/chatbot/conversations/` - List conversations
- `GET /api/chatbot/papers/{id}/highlights/` - Get highlights

##  Testing

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test papers
python manage.py test chatbot

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

##  Deployment

### Production Settings
```python
# settings.py
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

### Docker Deployment
```dockerfile
# Dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["gunicorn", "reference_graph.wsgi:application"]
```

### Environment Variables for Production
```bash
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
DATABASE_URL=postgresql://user:pass@host:port/db
REDIS_URL=redis://redis:6379/0
```

## 🔍 Troubleshooting

### Common Issues

1. **Redis Connection Error**
   ```bash
   # Check if Redis is running
   redis-cli ping
   # Should return PONG
   ```

2. **OpenAI API Errors**
   - Verify API key in `.env`
   - Check API quota and billing
   - Ensure model name is correct

3. **File Upload Issues**
   - Check file size limits
   - Verify file format support
   - Check media directory permissions

4. **Database Migration Errors**
   ```bash
   python manage.py makemigrations --merge
   python manage.py migrate
   ```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT models
- ChromaDB for vector database
- Django community for the excellent framework
- Academic community for inspiration

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the troubleshooting section

## 🔮 Future Enhancements

- [ ] Multi-language support
- [ ] Advanced citation analysis
- [ ] Collaborative annotation
- [ ] Export to various formats
- [ ] Integration with academic databases
- [ ] Mobile app development
- [ ] Advanced graph algorithms
- [ ] Real-time collaboration

---

**Built with ❤️ for the academic community**
# ResearchPaperAnalyzer
