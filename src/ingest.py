import os,logging
from pathlib import Path
from docling.document_converter import DocumentConverter

class Ingest:

    supported = {".pdf", ".txt"}

    def load(self,path: Path):
        if not os.path.exists(path): raise FileNotFoundError(f"{path} not found")
        if os.path.isfile(path):
            self._load_file(path)
        else:
            for file in path.glob("*"):
                if file.suffix in self.supported:
                    self._load_file(file)
                else: logging.debug(f"Skip file {file}")

    def _load_file(self,path: Path):
        if path.suffix not in self.supported:
            raise Exception(f"File extension not supported. Supported extensions are {self.supported}")
        logging.info(f"Processing file {path}")
        converter = DocumentConverter()
        doc = converter.convert(path).document
        logging.info(doc.export_to_markdown())


