from abc import ABC
from datetime import date

from pydantic import BaseModel, field_validator
from typing import Self, TypeVar, Generic

class BaseDateModel(BaseModel):
    start_date: date | None
    end_date: date | None

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def parse_null(cls, v):
        if v == "null" or v == "":
            return None
        return v


class Context(BaseDateModel):
    category: str
    content: str
    summary: str

class Chunk(BaseModel):
    chunk_index: int
    content: str
    #TODO metadata

class Document(BaseModel):
    document_id: str
    document_name: str
    context: Context
    chunks: list[Chunk]

class CommonPayload(BaseDateModel, ABC):
    document_id: str
    category: str
    content: str

class ContextPayload(CommonPayload):
    summary: str

    @classmethod
    def from_context(cls, document_id: str, context: Context) -> Self:
        return cls(
            document_id=document_id,
            category=context.category,
            start_date=context.start_date,
            end_date=context.end_date,
            content=context.content,
            summary=context.summary
        )

class UniversePayload(CommonPayload):
    chunk_index: int

    @classmethod
    def from_document(cls, doc: Document, chunk: Chunk) -> Self:
        return cls(
            document_id=doc.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            category=doc.context.category,
            start_date=doc.context.start_date,
            end_date=doc.context.end_date
        )

class ContextFilterScore(BaseModel):
    score: float
    reason: str

T = TypeVar("T", UniversePayload, ContextPayload)
class SearchResult(BaseModel, Generic[T]):
    payload: T
    score: float
    context_score: ContextFilterScore | None

class ClassifiedQuery(BaseDateModel):
    categories: list[str]
    optimized_query: str
    user_query: str

class Picker(BaseModel):
    thought:str
    selected:str
    confidence:float