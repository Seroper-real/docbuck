import hashlib
from pathlib import Path


def hash_file(file: Path) -> str:
    if not file.is_file(): raise FileNotFoundError(f"File not valid for hashing {file}")
    sha256_hash = hashlib.sha256()
    with open(file, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()