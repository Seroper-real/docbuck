LOG_LEVEL  = "DEBUG"   # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
LOG_DATEFMT = "%Y-%m-%d %H:%M:%S"

#QDRANT
QDRANT_URL = "http://localhost:6333" #Or use ":memory:"
COLLECTION_NAME = "test_collection"
QD_MODEL_NAME = "intfloat/multilingual-e5-large"

#OLLAMA
OL_CHAT_MODEL = "llama3:latest"
OL_CHAT_LANGUAGE = "italian"
OL_CLASSIFY_MODEL = "qwen2.5:3b"

OL_SUMMARIZE_MODEL = "llama3:latest"
OL_SUMMARIZE_MODEL_CONTEXT_WINDOW = 4096