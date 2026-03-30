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

    def upload_chunked_document(self, doc_name:str, file_hash:str, chunks:list[BaseChunk]) -> None:
        self.client.upsert(
            self.collection_name,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=models.Document(text=chunk.text, model=self.model_name),
                    payload=ChunkPayload(document_id=doc_name,file_hash=file_hash,chunk_index=i,content=chunk.text).model_dump()
                ) for i,chunk in enumerate(chunks)
            ]
        )

    def query_points(self, text:str) -> list[ScoredPoint]:
        logging.debug(f"Search query: {text}")
        return self.client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=text,
                model=self.model_name
            )
        ).points

    def get_context_results(self, text:str) -> str:
        search_results : list[ScoredPoint] = self.query_points(text)
        formatted_chunks = []
        for hit in search_results:
            data = ChunkPayload(**hit.payload)
            chunk_text = f"[File: {data.document_id} | Chunk: {data.chunk_index} | Content:{data.content}]"
            formatted_chunks.append(chunk_text)
        logging.debug(f"Formatted Chunks:\n{formatted_chunks}")
        return "\n".join(formatted_chunks)

    def get_full_document_context(self, doc_name: str) -> str:
        #TODO da implementare e testare
        results = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="document_id", match=models.MatchValue(value=doc_name)),
                ]
            ),
            limit=100,
            with_payload=True,
            with_vectors=False,
        )
        sorted_chunks = sorted(results[0], key=lambda x: x.payload['chunk'])
        return "\n".join([c.payload['content'] for c in sorted_chunks])

    def document_exist(self, hash_file:str) -> bool:
        result = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="file_hash", match=models.MatchValue(value=hash_file))
                ]
            )
        )
        return len(result[0]) > 0