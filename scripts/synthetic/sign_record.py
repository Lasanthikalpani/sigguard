# scripts/synthetic/sign_record.py

import sys
sys.path.append("src")

from PIL import Image
from sigguard.crypto import rsa_sign
from scripts.synthetic.hash_generator import (
    compute_content_hash, compute_metadata_hash, compute_phash
)

PRIVATE_KEY = "data/rq3_dataset/rsa_keys/gov_private_key.pem"


def sign_record(record: dict) -> dict:
    """
    Add hashes + pHash + RSA signature + QR payload to a record.
    Timestamp is intentionally excluded from QR (Timestamp-QR fix).
    """
    # 0. Validate
    for k in ["content_text", "issuer", "document_id",
              "document_type", "rendered_image_path"]:
        if k not in record:
            raise ValueError(f"Missing required field: {k}")

    # 1. Hashes
    record["content_hash"]  = compute_content_hash(record["content_text"])
    record["metadata_hash"] = compute_metadata_hash(
        record["issuer"], record["document_id"])

    # 2. Perceptual hash
    record["phash"] = compute_phash(Image.open(record["rendered_image_path"]))

    # 3. RSA sign (තැන 1)
    record["signature"] = rsa_sign(
        record["content_hash"], record["metadata_hash"], PRIVATE_KEY)

    # 4. QR payload (no timestamp)
    record["qr_payload"] = {
        "content_hash":  record["content_hash"],
        "metadata_hash": record["metadata_hash"],
        "phash":         record["phash"],
        "signature":     record["signature"],
        "issuer":        record["issuer"],
        "document_id":   record["document_id"],
        "document_type": record["document_type"],
    }
    assert "timestamp" not in record["qr_payload"], \
        "Timestamp must NOT be in QR (Timestamp-QR fix)"
    return record