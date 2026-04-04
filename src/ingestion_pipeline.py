import logging
import os
import uuid
from pathlib import Path

from pydantic import UUID4

import util
from cortex import Cortex
from document_reader import DocumentReader
from models import Context, Document
from qdrant import Qdrant


class IngestionPipeline:

    def __init__(self):
        self.qdrant = Qdrant()
        self.document_reader = DocumentReader()
        self.cortex = Cortex()
        pass

    def load(self,path: Path) -> None:
        if not os.path.exists(path): raise FileNotFoundError(f"{path} not found")
        if os.path.isfile(path):
            self._load_file(path)
        else:
            for file in path.glob("*"):
                if self.document_reader.is_file_supported(file):
                    self._load_file(file)
                else: logging.debug(f"Skip file {file}")

    def _load_file(self,path: Path) -> None:
        if not self.document_reader.is_file_supported(path):
            raise Exception(f"File extension not supported. Supported extensions are {self.document_reader.get_supported()}")
        file_hash = util.hash_file(path)
        if self.qdrant.document_exist(file_hash):
            logging.info(f"Skipping file {path} because a file with hash {file_hash} is already present")
            return
        logging.info(f"Processing file {path}")
        chunks = self.document_reader.get_chunks(path)
        logging.debug(f"Extracted Chunks: {chunks}")
        doc_name = path.name
        categories: set[str] = self.qdrant.get_categories()
        context: Context = self.cortex.extract_context_info(chunks, categories)
        document: Document = Document(document_id=str(uuid.uuid4()),file_hash=file_hash,context=context,chunks=chunks)
        self.qdrant.upload_document(document)
