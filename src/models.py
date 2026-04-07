from abc import ABC
from pydantic import BaseModel
from typing import Optional, Literal, Self


class Context(BaseModel):
    category: str
    start_date: str | None
    end_date: str | None
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

class CommonPayload(BaseModel, ABC):
    document_id: str
    category: str
    start_date: str | None
    end_date: str | None
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

##before
class ClassifyResult(BaseModel):
    intent: Literal["SEARCH","SUMMARIZE","DOCUMENT_SPECIFIC"]
    target_file: Optional[str] = None
    user_query_optimized: str

    class Config:
        # Permette di gestire eventuali campi extra nel JSON senza errore
        extra = "ignore"