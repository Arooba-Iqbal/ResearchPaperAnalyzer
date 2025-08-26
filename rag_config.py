# RAG Engine Configuration
# Set this to False to disable Ollama and use simple responses
USE_OLLAMA = False

# Set this to True if you want to use OpenAI embeddings
USE_OPENAI = False

# Local embedding model
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'

# Number of top chunks to retrieve
RAG_TOP_K = 5

# Ollama settings (only used if USE_OLLAMA = True)
OLLAMA_HOST = 'http://localhost:11434'
OLLAMA_MODEL = 'mistral'

# OpenAI settings (only used if USE_OPENAI = True)
OPENAI_API_KEY = ''
OPENAI_MODEL = 'text-embedding-ada-002'
