import logging
import os
from pathlib import Path
from typing import Callable

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
        self.categories: set[str] = set(line.strip() for line in Path("resources/categories.txt").read_text().splitlines() if line.strip())


    def load(self, path: Path) -> None:
        self.process(path,self._load_file)

    def delete(self, path: Path) -> None:
        self.process(path,self._delete_file)

    def process(self, path: Path, on_file: Callable[[Path], None]) -> None:
        if not os.path.exists(path): raise FileNotFoundError(f"{path} not found")
        if os.path.isfile(path):
            if not self.document_reader.is_file_supported(path):
                raise Exception(f"File extension not supported. Supported extensions are {self.document_reader.get_supported()}")
            on_file(path)
        else:
            for file in path.glob("*"):
                if self.document_reader.is_file_supported(file):
                    on_file(file)
                else: logging.debug(f"Skip file {file}")

    def _load_file(self,path: Path) -> None:
        document_id = util.generate_document_id(path)
        if self.qdrant.document_exist(document_id):
            logging.info(f"Skipping file {path} because a file with id {document_id} is already present")
            return
        logging.info(f"Processing file {path}")
        chunks = self.document_reader.get_chunks(path)
        logging.debug(f"Extracted Chunks: {chunks}")
        doc_name = path.name
        db_categories: set[str] = self.qdrant.get_categories()
        self.categories |= db_categories
        context: Context = self.cortex.extract_context_info(chunks, self.categories)
        document: Document = Document(document_id=document_id,document_name=doc_name,context=context,chunks=chunks)
        self.qdrant.upload_document(document)

    def _delete_file(self,path: Path) -> None:
        self.qdrant.delete_document(util.generate_document_id(path))