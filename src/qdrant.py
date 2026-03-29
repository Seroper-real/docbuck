import logging
import uuid

from docling_core.transforms.chunker import BaseChunk
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import ScoredPoint

import config
from models import ChunkPayload


class Qdrant:

    def __init__(self):
        self.client = QdrantClient(config.QDRANT_URL)
        self.collection_name = config.COLLECTION_NAME
        self.model_name = config.QD_MODEL_NAME

        if not self.client.collection_exists(self.collection_name):
            logging.info(f"Creating a new qdrant collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=self.client.get_embedding_size(self.model_name),
                    distance=models.Distance.COSINE
                ),  # size and distance are model dependent
        )

    def upload_chunked_document(self, doc_name:str, chunks:list[BaseChunk]):
        self.client.upsert(
            self.collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=models.Document(text=chunk.text, model=self.model_name),
                    payload=ChunkPayload(document_id=doc_name,chunk_index=i,content=chunk.text).model_dump()
                ) for i,chunk in enumerate(chunks)
            ]
        )

    def query_points(self, text:str) -> list[ScoredPoint]:
        return self.client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=text,
                model=self.model_name
            )
        ).points

    def get_context_results(self, text:str) -> str:
        search_results = self.query_points(text)
        return "\n---\n".join([hit.payload['content'] for hit in search_results]) #TODO formattare contesto, aggiungere nome file e chunck