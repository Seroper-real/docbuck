LOG_LEVEL  = "INFO"   # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

#QDRANT
QDRANT_URL = "http://localhost:6333" #Or use ":memory:"
COLLECTION_NAME = "test_collection"
QD_MODEL_NAME = "BAAI/bge-small-en"

#OLLAMA
OL_CHAT_MODEL_NAME = "llama3:latest"