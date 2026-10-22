# src/sigguard/api/hybrid_routes.py

from datetime import datetime
import io
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from PIL import Image

from sigguard.crypto import (
    rsa_sign, compute_content_hash, compute_metadata_hash, compute_phash
)
from sigguard.blockchain.router import route_to_node
from sigguard.blockchain.ledger_writer import write_block

router = APIRouter()

PRIVATE_KEY = "data/rq3_dataset/rsa_keys/gov_private_key.pem"


@router.post("/issue")
async def issue_document(
    document: UploadFile = File(...),
    signature: UploadFile = File(...),
    document_id: str = Form(...),
    document_type: str = Form(...),          # ← එකතු කළා
    issuer: str = Form("Government of Sri Lanka"),
):
    # 1. Read inputs
    content_bytes   = await document.read()
    signature_bytes = await signature.read()        # ← දැන් කියවයි
    content_text    = content_bytes.decode("utf-8", errors="ignore")

    # 2. Compute hashes
    content_hash  = compute_content_hash(content_text)
    metadata_hash = compute_metadata_hash(issuer, document_id)
    phash         = compute_phash(Image.open(io.BytesIO(content_bytes)))  # ← එකතු කළා

    # 3. RSA sign (තැන 1 — නිවැරදි)
    signature_hex = rsa_sign(content_hash, metadata_hash, PRIVATE_KEY)

    # 4. Build QR payload (timestamp NOT included — Timestamp-QR fix)
    qr_payload = {
        "content_hash":  content_hash,
        "metadata_hash": metadata_hash,
        "signature":     signature_hex,
        "issuer":        issuer,
        "document_id":   document_id,
        "document_type": document_type,
    }
    assert "timestamp" not in qr_payload, "Timestamp must NOT be in QR"

    # 5. Write to group-wise blockchain node
    node_path = route_to_node(document_type)
    issued_at = datetime.utcnow().isoformat() + "Z"
    write_block(
        node_path=node_path,
        document_id=document_id,
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        phash=phash,
        signature=signature_hex,
        issuer=issuer,
        issued_at=issued_at,
        document_type=document_type,
        amends=None,
        copy_of=None,
    )

    return {
        "document_id":   document_id,
        "document_type": document_type,
        "content_hash":  content_hash,
        "metadata_hash": metadata_hash,
        "phash":         phash,                   # ← එකතු කළා
        "signature":     signature_hex,
        "issuer":        issuer,
        "issued_at":     issued_at,               # ← සැබෑ timestamp
        "node":          node_path,               # ← කුමන node එකට ලිව්වාද
        "qr_payload":    qr_payload,              # ← QR එකට embed කිරීමට
        "timestamp_stored_in_blockchain_only": True,
    }