# scripts/synthetic/hash_generator.py

import hashlib
import json
from PIL import Image
import imagehash


def compute_content_hash(content: str | bytes) -> str:
    if isinstance(content, str):
        content = content.strip().replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def compute_metadata_hash(issuer: str, document_id: str) -> str:
    payload = json.dumps(
        {"issuer": issuer, "document_id": document_id},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def compute_phash(doc_image: Image.Image, hash_size: int = 8) -> str:
    if doc_image.mode not in ("L", "RGB"):
        doc_image = doc_image.convert("RGB")
    if doc_image.mode == "RGB":
        doc_image = doc_image.convert("L")
    ph = imagehash.phash(doc_image, hash_size=hash_size)
    return format(int(str(ph), 16), f"0{hash_size*hash_size}b")


def hamming_distance(h1: str, h2: str) -> int:
    if len(h1) != len(h2):
        raise ValueError(f"Hash length mismatch: {len(h1)} vs {len(h2)}")
    return sum(a != b for a, b in zip(h1, h2))