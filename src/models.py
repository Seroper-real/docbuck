from pydantic import BaseModel
from typing import Optional, Literal

class ChunkPayload(BaseModel):
    document_id: str
    file_hash: str
    chunk_index: int
    content: str

class ClassifyResult(BaseModel):
    intent: Literal["SEARCH","SUMMARIZE","DOCUMENT_SPECIFIC"]
    target_file: Optional[str] = None
    user_query_optimized: str

    class Config:
        # Permette di gestire eventuali campi extra nel JSON senza errore
        extra = "ignore"