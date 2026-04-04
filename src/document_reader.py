import os,logging
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HybridChunker, BaseChunk

import util
from models import Chunk
from qdrant import Qdrant


class DocumentReader:

    supported = {".pdf", ".txt"}

    def __init__(self):
        self.converter = DocumentConverter()
        self.chunker = HybridChunker()

    def is_file_supported(self, path : Path) -> bool:
        return path.is_file() and path.suffix in self.supported

    def get_chunks(self, path : Path) -> list[Chunk]:
        # TODO check and add metadata from dockling
        doc = self.converter.convert(path).document
        return [
            Chunk(chunk_index=i, content=chunk.text)
                for i, chunk in enumerate(self.chunker.chunk(dl_doc=doc))
        ]

    def get_supported(self) -> set[str]:
        return self.supported