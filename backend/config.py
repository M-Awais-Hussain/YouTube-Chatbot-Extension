import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    LLM_MODEL = "llama3-8b-8192"
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    MAX_RETRIES = 3
    CACHE_EXPIRATION = 3600  # 1 hour in seconds
    # Server configuration
    HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT = int(os.getenv('FLASK_PORT', 5000))
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 't')