import os,logging
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling_core.transforms.chunker import HybridChunker

import util
from qdrant import Qdrant


class Ingest:
    supported = {".pdf", ".txt"}

    def __init__(self, qdrant:Qdrant):
        self.converter = DocumentConverter()
        self.chunker = HybridChunker()
        self.qdrant = qdrant


    def load(self,path: Path) -> None:
        if not os.path.exists(path): raise FileNotFoundError(f"{path} not found")
        if os.path.isfile(path):
            self._load_file(path)
        else:
            for file in path.glob("*"):
                if file.suffix in self.supported:
                    self._load_file(file)
                else: logging.debug(f"Skip file {file}")

    def _load_file(self,path: Path) -> None:
        if path.suffix not in self.supported:
            raise Exception(f"File extension not supported. Supported extensions are {self.supported}")
        file_hash = util.hash_file(path)
        if self.qdrant.document_exist(file_hash):
            logging.info(f"Skipping file {path} because qdrant has already a file with hash {file_hash}")
            return
        logging.info(f"Processing file {path}")
        doc = self.converter.convert(path).document
        chunks = list(self.chunker.chunk(dl_doc=doc))
        # TODO check and add metadata from dockling
        logging.debug(f"Extracted Chunks: {chunks}")
        doc_name = path.name
        self.qdrant.upload_chunked_document(doc_name, file_hash, chunks)
