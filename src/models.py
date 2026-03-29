from pydantic import BaseModel

class ChunkPayload(BaseModel):
    document_id: str
    chunk_index: int
    content: str
