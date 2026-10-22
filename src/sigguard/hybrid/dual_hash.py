# src/sigguard/hybrid/dual_hash.py

import hashlib
import json
from PIL import Image
import imagehash

def compute_content_hash(content_text: str) -> str:
    """SHA-256 of document content (Timestamp-QR p.2)."""
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()

def compute_metadata_hash(issuer: str, document_id: str) -> str:
    """SHA-256(issuer + doc_id) — timestamp REMOVED (Timestamp-QR solution)."""
    payload = f"{issuer}|{document_id}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def compute_phash(image: Image.Image) -> str:
    """64-bit perceptual hash as binary string (Dual-Hash p.7)."""
    ph = imagehash.phash(image, hash_size=8)
    return bin(int(str(ph), 16))[2:].zfill(64)

def hamming_distance(hash1: str, hash2: str) -> int:
    """Number of differing bits (Dual-Hash p.7)."""
    if len(hash1) != len(hash2):
        raise ValueError("Hash lengths must match")
    return sum(b1 != b2 for b1, b2 in zip(hash1, hash2))

PHASH_THRESHOLD = 10  # Dual-Hash p.8: Hamming ≤ 10 → PHOTOCOPY