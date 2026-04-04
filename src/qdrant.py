import logging
import uuid
from typing import Any

from docling_core.transforms.chunker import BaseChunk
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import ScoredPoint

import config
from models import Chunk, Document, ChunkPayload


class Qdrant:

    def __init__(self):
        self.client = QdrantClient(config.QDRANT_URL)
        self.collection_universe = config.COLLECTION_UNIVERSE
        self.collection_context = config.COLLECTION_CONTEXT
        self.model_name = config.QD_MODEL_NAME
        self._create_collection_if_not_exits(self.collection_universe)
        self._create_collection_if_not_exits(self.collection_context)

    def _create_collection_if_not_exits(self, name):
        if not self.client.collection_exists(name):
            logging.info(f"Creating a new qdrant collection: {name}")
            self.client.create_collection(
                collection_name=name,
                vectors_config=models.VectorParams(
                    size=self.client.get_embedding_size(self.model_name),
                    distance=models.Distance.COSINE
                ),  # size and distance are model dependent
        )

    def get_categories(self) -> set[str]:
        categories: set[str] = set()
        next_offset = None
        field = "category"
        while True:
            points, next_offset = self.client.scroll(
                collection_name=self.collection_context,
                with_payload=[field],
                with_vectors=False,
                limit=1000,
                offset=next_offset
            )
            for point in points:
                if field in point.payload:
                    categories.add(point.payload[field])

            if next_offset is None:
                break
        return categories

    def upload_document(self, document:Document) -> None:
        #upload the summary to context collection
        self.client.upsert(
            self.collection_context,
            points=[
                models.PointStruct(
                    id=document.document_id,
                    vector=models.Document(text=document.context.summary, model=self.model_name),
                    payload=document.context.model_dump()
                )
            ]
        )
        #upload all chunks to universe collection
        self.client.upsert(
            self.collection_universe,
            points=[
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=models.Document(text=chunk.content, model=self.model_name),
                    payload=ChunkPayload.from_document(document,chunk).model_dump()
                ) for chunk in document.chunks
            ]
        )

    ### Before
    def query_points(self, text:str) -> list[ScoredPoint]:
        logging.debug(f"Search query: {text}")
        return self.client.query_points(
            collection_name=self.collection_universe,
            query=models.Document(
                text=text,
                model=self.model_name
            )
        ).points

    def get_context_results(self, text:str) -> str:
        search_results : list[ScoredPoint] = self.query_points(text)
        formatted_chunks = []
        for hit in search_results:
            data = Chunk(**hit.payload)
            chunk_text = f"[File: {data.document_id} | Chunk: {data.chunk_index} | Content:{data.content}]"
            formatted_chunks.append(chunk_text)
        logging.debug(f"Formatted Chunks:\n{formatted_chunks}")
        return "\n".join(formatted_chunks)

    def get_full_document_context(self, doc_name: str) -> str:
        #TODO da implementare e testare
        results = self.client.scroll(
            collection_name=self.collection_universe,
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
            collection_name=self.collection_universe,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key="file_hash", match=models.MatchValue(value=hash_file))
                ]
            )
        )
        return len(result[0]) > 0