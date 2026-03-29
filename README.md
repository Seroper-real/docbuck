# docbuck

## Requirements
Have ollama and the models downloaded
Have qdrant up and running:
docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant