import hashlib
import uuid
from pathlib import Path

MY_NAMESPACE = uuid.UUID("01fea438-ff69-4ac3-a0f1-4649c6799cab")

def hash_file(file: Path) -> str:
    if not file.is_file(): raise FileNotFoundError(f"File not valid for hashing {file}")
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def generate_document_id(file: Path) -> str:
    return str(uuid.uuid5(MY_NAMESPACE, hash_file(file)))