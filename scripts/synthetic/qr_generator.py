# scripts/synthetic/qr_generator.py
"""
QR Code Generation for SigVerify RQ3 Hybrid System.

Timestamp is NOT included in the QR payload (see Timestamp-QR solution).
Timestamp is stored only in blockchain issued_at field.
"""

import json
import os
import qrcode
from qrcode.constants import ERROR_CORRECT_H
from PIL import Image


def generate_qr(qr_payload: dict, output_path: str,
                box_size: int = 10, border: int = 4) -> str:
    """
    Generate a QR code image from a payload dict.

    Args:
        qr_payload: dict with keys content_hash, metadata_hash,
                    signature, issuer, document_id, document_type
        output_path: where to save the PNG
        box_size: pixels per QR module (10 is good for 600 DPI)
        border: quiet zone modules

    Returns:
        output_path
    """
    # Validate payload (no timestamp allowed — Timestamp-QR fix)
    if "timestamp" in qr_payload:
        raise ValueError(
            "Timestamp must NOT be in QR payload. "
            "Store it in blockchain issued_at field instead."
        )

    required = {"content_hash", "metadata_hash", "signature",
                "issuer", "document_id", "document_type"}
    missing = required - qr_payload.keys()
    if missing:
        raise ValueError(f"QR payload missing fields: {missing}")

    qr = qrcode.QRCode(
        version=4,
        error_correction=ERROR_CORRECT_H,  # 30% damage recovery
        box_size=box_size,
        border=border,
    )
    qr.add_data(json.dumps(qr_payload, sort_keys=True))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img.save(output_path)
    return output_path


def embed_qr_in_document(doc_image: Image.Image, qr_path: str,
                         position: tuple = (2000, 200)) -> Image.Image:
    """
    Paste the QR code onto the document image at the given position.
    Typical position: top-right corner of A4 at 600 DPI.
    """
    qr_img = Image.open(qr_path).convert("RGB")
    # QR should be ~300x300 px at 600 DPI
    qr_img = qr_img.resize((300, 300), Image.LANCZOS)
    doc = doc_image.copy()
    doc.paste(qr_img, position)
    return doc