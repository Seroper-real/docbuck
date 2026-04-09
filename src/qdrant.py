import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient, models
from qdrant_client.models import ScoredPoint, Filter, FieldCondition, MatchValue, MatchAny

import config
from models import Chunk, Document, UniversePayload, ContextPayload, ClassifiedQuery, SearchResult


class Qdrant:
    DOCUMENT_ID_FIELD = "document_id"
    CATEGORY_FIELD = "category"

    def __init__(self):
        self.client = QdrantClient(config.QDRANT_URL)
        self.collection_universe = config.COLLECTION_UNIVERSE
        self.collection_context = config.COLLECTION_CONTEXT
        self.model_name = config.QD_MODEL_NAME
        self._create_collection_if_not_exits(self.collection_universe)
        self._create_collection_if_not_exits(self.collection_context)
        self.initial_categories: set[str] = set(line.strip() for line in Path("resources/categories.txt").read_text().splitlines() if line.strip())

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
        categories = self._get_categories_on_db()
        categories |= self.initial_categories
        return categories

    def _get_categories_on_db(self) -> set[str]:
        categories: set[str] = set()
        next_offset = None
        field = self.CATEGORY_FIELD
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

    def document_exist(self, document_id:str) -> bool:
        result = self.client.scroll(
            collection_name=self.collection_universe,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(key=self.DOCUMENT_ID_FIELD, match=models.MatchValue(value=document_id))
                ]
            )
        )
        return len(result[0]) > 0

    def upload_document(self, document:Document) -> None:
        #upload the summary to context collection
        self.client.upsert(
            self.collection_context,
            points=[
                models.PointStruct(
                    id=document.document_id,
                    vector=models.Document(text=document.context.summary, model=self.model_name),
                    payload=ContextPayload.from_context(document.document_id,document.context).model_dump()
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
                    payload=UniversePayload.from_document(document, chunk).model_dump()
                ) for chunk in document.chunks
            ]
        )

    def _delete_document(self, collection_name:str, document_id:str):
        self.client.delete(
            collection_name,
            points_selector=Filter(
                must=[FieldCondition(key=self.DOCUMENT_ID_FIELD, match=MatchValue(value=document_id))]
            )
        )

    def delete_document(self, document_id:str):
        self._delete_document(self.collection_context,document_id)
        self._delete_document(self.collection_universe,document_id)

    def search_context(self, query: ClassifiedQuery, limit: int = 50, score_threshold: float = 0.5) -> list[SearchResult[ContextPayload]]:
        logging.debug(f"context_search - Search query: {query}")
        conditions = []
        if query.categories:
            conditions.append(
                FieldCondition(
                    key="category",
                    match=MatchAny(any=query.categories)
                )
            )
        if query.start_date:
            conditions.append(
                FieldCondition(
                    key="start_date",
                    range=models.DatetimeRange(gte=datetime(query.start_date.year, query.start_date.month, query.start_date.day,tzinfo=timezone.utc))
                )
            )

        if query.end_date:
            conditions.append(
                FieldCondition(
                    key="start_date",
                    range=models.DatetimeRange(lte=datetime(query.end_date.year, query.end_date.month, query.end_date.day,tzinfo=timezone.utc))
                )
            )

        search_filter = Filter(must=conditions) if conditions else None

        results = self.client.query_points(
            collection_name=self.collection_context,
            query=models.Document(
                text=query.optimized_query,
                model=self.model_name
            ),
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold
        ).points

        return [
            SearchResult(
                payload=ContextPayload(**point.payload), score=point.score, context_score=None
            ) for point in results
        ]

    def search_universe(self, query: ClassifiedQuery, document_ids: list[str], limit: int = 100, score_threshold: float = 0.3) -> list[SearchResult[UniversePayload]]:
        search_filter = Filter(
            must=[
                FieldCondition(
                    key=self.DOCUMENT_ID_FIELD,
                    match=MatchAny(any=document_ids)
                )
            ]
        )

        results = self.client.query_points(
            collection_name=self.collection_universe,
            query=models.Document(
                text=query.optimized_query,
                model=self.model_name
            ),
            query_filter=search_filter,
            limit=limit,
            score_threshold=score_threshold
        ).points

        return [
            SearchResult[UniversePayload](
                payload=UniversePayload(**point.payload),
                score=point.score,
                context_score=None
            )
            for point in results
        ]

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
