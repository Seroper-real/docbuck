from pydantic import BaseModel
from typing import Optional, Literal, Self


class Context(BaseModel):
    category: str
    start_date: str | None
    end_date: str | None
    text: str
    summary: str

class Chunk(BaseModel):
    chunk_index: int
    content: str
    #TODO metadata

class Document(BaseModel):
    document_id: str
    file_hash: str
    context: Context
    chunks: list[Chunk]

class ChunkPayload(BaseModel):
    """
    For Saving Chunks in Qdrant
    """
    document_id: str
    file_hash: str
    chunk_index: int
    content: str
    category: str
    start_date: str | None
    end_date: str | None

    @classmethod
    def from_document(cls, doc: Document, chunk: Chunk) -> Self:
        """
        Custom factory to map a Document and a specific Chunk into a ChunkPayload.
        """
        return cls(
            document_id=doc.document_id,
            file_hash=doc.file_hash,
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