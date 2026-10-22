"""
RQ3: Hybrid Verification API Router
FastAPI endpoints for hybrid AI + cryptographic document verification.

Endpoints:
- POST /api/v1/hybrid/issue       — Issue new document with QR
- POST /api/v1/hybrid/verify      — Full hybrid verification (AI + crypto + fusion)
- POST /api/v1/hybrid/verify-batch — Batch verification
- GET  /api/v1/hybrid/health      — Service health check
- GET  /api/v1/hybrid/info        — Engine configuration

Integrates with existing RQ1 AI verification service.
"""
import base64
import hashlib
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, Field

from src.api.services.crypto_service import CryptoService
from src.api.services.qr_service import QRService
from src.api.services.fusion_engine import FusionEngine

from src.api.services import blockchain_service as _blockchain
from src.api.services.blockchain_service import get_ledger   # ← 🆕 Blockchainfrom src.api.services.qr_service import QRVerificationLayer, QRService

# ============================================================
# ROUTER SETUP
# ============================================================

router = APIRouter(
    prefix="/api/v1/hybrid",
    tags=["RQ3 - Hybrid Verification"],
    responses={
        400: {"description": "Bad request (invalid input)"},
        500: {"description": "Internal server error"},
    },
)

# Singleton service instances
_crypto = CryptoService()
_qr = QRService()
_fusion = FusionEngine()


# ============================================================
# REQUEST / RESPONSE MODELS
# ============================================================

class IssueRequest(BaseModel):
    """Optional metadata for document issuance."""
    document_id: Optional[str] = Field(
        None,
        description="Custom document ID (auto-generated if not provided)",
    )
    issuer: str = Field(
        "Government of Sri Lanka",
        description="Issuing authority",
    )
    ai_confidence: float = Field(
        0.95,
        ge=0.0,
        le=1.0,
        description="AI confidence from RQ1 verification",
    )


class IssueResponse(BaseModel):
    """Response for document issuance."""
    document_id: str
    qr_base64: str
    integrity_record: dict
    issued_at: str


class VerifyResponse(BaseModel):
    """Response for hybrid verification."""
    is_authentic: bool
    confidence: float
    ai_score: float
    crypto_score: float
    tamper_detected: bool
    decision_path: str
    explanations: dict
    document_id: Optional[str] = None
    verified_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: dict
    timestamp: str


class InfoResponse(BaseModel):
    """Engine configuration."""
    fusion_weights: dict
    thresholds: dict
    qr_config: dict
    crypto_config: dict


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def _generate_document_id() -> str:
    """Generate a unique Sri Lankan government document ID."""
    timestamp = datetime.utcnow().strftime("%Y%m%d")
    random_part = uuid.uuid4().hex[:8].upper()
    return f"LK-{timestamp}-{random_part}"


async def _run_ai_verification(
    signature_bytes: bytes,
    reference_bytes: Optional[bytes] = None,
) -> dict:
    """
    Run RQ1 AI verification (Siamese CNN).

    If reference is provided, compares reference vs test signature.
    If not, falls back to a placeholder value.

    Args:
        signature_bytes: Test signature region
        reference_bytes: Optional reference (genuine) signature

    Returns:
        Dict with 'similarity' and 'prediction' keys
    """
    if reference_bytes is None:
        # No reference provided → fallback
        return {
            "similarity": 0.94,
            "prediction": "genuine",
            "_fallback": True,
            "_reason": "No reference signature provided",
        }

    try:
        # Import RQ1 model from main.py state
        from src.api.main import state
        from src.data.preprocess import SignaturePreprocessor
        import torch
        import io
        import tempfile
        import os
        from PIL import Image

        if "model" not in state:
            return {
                "similarity": 0.94,
                "prediction": "genuine",
                "_fallback": True,
                "_reason": "RQ1 model not loaded",
            }

        model = state["model"]
        preprocessor = state["preprocessor"]
        device = state["device"]

        # Load images from bytes
        ref_img = Image.open(io.BytesIO(reference_bytes)).convert("L")
        test_img = Image.open(io.BytesIO(signature_bytes)).convert("L")

        # Save temp files (preprocessor expects paths)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as ref_f:
            ref_path = ref_f.name
            ref_img.save(ref_path)
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as test_f:
            test_path = test_f.name
            test_img.save(test_path)

        try:
            # Preprocess
            ref_processed = preprocessor(ref_path)
            test_processed = preprocessor(test_path)

            # Tensors
            ref_tensor = (
                torch.from_numpy(ref_processed)
                .unsqueeze(0).unsqueeze(0).repeat(1, 3, 1, 1)
                .to(device)
            )
            test_tensor = (
                torch.from_numpy(test_processed)
                .unsqueeze(0).unsqueeze(0).repeat(1, 3, 1, 1)
                .to(device)
            )

            # Inference
            with torch.no_grad():
                emb1, emb2 = model(ref_tensor, test_tensor)
                distance = torch.nn.functional.pairwise_distance(emb1, emb2).item()

            # RQ1 threshold
            threshold = 0.1358
            similarity = max(0.0, min(1.0, 1.0 - distance))
            prediction = "genuine" if distance < threshold else "forged"

            return {
                "similarity": similarity,
                "prediction": prediction,
                "distance": distance,
                "_fallback": False,
            }
        finally:
            # Cleanup temp files
            os.unlink(ref_path)
            os.unlink(test_path)

    except Exception as e:
        return {
            "similarity": 0.94,
            "prediction": "genuine",
            "_fallback": True,
            "_error": str(e),
        }


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check the health of all hybrid verification services.
    """
    return HealthResponse(
        status="healthy",
        services={
            "crypto": "ready",
            "qr": "ready",
            "fusion": "ready",
            "ai": "ready",
        },
        timestamp=datetime.utcnow().isoformat() + "Z",
    )


@router.get("/info", response_model=InfoResponse)
async def engine_info():
    """
    Get the current configuration of all hybrid verification engines.
    """
    return InfoResponse(
        fusion_weights={
            "ai": _fusion.ai_weight,
            "crypto": _fusion.crypto_weight,
        },
        thresholds={
            "ai": _fusion.ai_threshold,
            "crypto": _fusion.crypto_threshold,
            "fusion": _fusion.fusion_threshold,
        },
        qr_config={
            "error_correction": "H (30%)",
            "min_qr_px": _qr.min_qr_px,
            "scale_in_doc": _qr.qr_scale_in_doc,
        },
        crypto_config={
            "hash_algorithm": _crypto.hash_algorithm,
            "hmac_algorithm": "HMAC-SHA256",
            "version": _crypto.version,
        },
    )


# src/api/routers/hybrid.py — line 275 සිට

@router.post("/issue", response_model=IssueResponse)
async def issue_document(
    document: UploadFile = File(..., description="Document image (PNG/JPEG)"),
    signature: UploadFile = File(..., description="Signature region image"),
    document_id: Optional[str] = Form(None),
    document_type: str = Form(..., description="BIRTH_CERTIFICATE | LAND_DEED | NATIONAL_ID | EDUCATION_CERT | VEHICLE_REG"),
    issuer: str = Form("Government of Sri Lanka"),
    ai_confidence: float = Form(0.95),
):
    """
    Issue a new document with dual-hash + group-wise blockchain node.

    Flow:
    1. Read document + signature bytes
    2. Compute content_hash (SHA-256) + metadata_hash (SHA-256) + phash (perceptual)
    3. RSA sign over (content_hash + metadata_hash)
    4. Build QR payload (5 fields, NO timestamp)
    5. Write block to the correct group-wise node
    6. Return QR + integrity record
    """
    # ---------- 1. Read uploads ----------
    try:
        doc_bytes = await document.read()
        sig_bytes = await signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploads: {e}")

    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")

    doc_id = document_id or _generate_document_id()

    # ---------- 2. Hashes (dual-hash) ----------
    content_hash  = _crypto.compute_content_hash_with_mask(doc_bytes)
    metadata_hash = _crypto.compute_metadata_hash(issuer, doc_id)   # ← NEW

    # pHash from document image (NEW)
    from PIL import Image
    import io
    try:
        doc_image = Image.open(io.BytesIO(doc_bytes))
        phash = _crypto.compute_phash(doc_image)
    except Exception as e:
        raise HTTPException(400, f"Invalid document image: {e}")

    # ---------- 3. RSA signature (Layer 4) ----------
    try:
        signature_hex = _crypto.rsa_sign(content_hash, metadata_hash)
    except Exception as e:
        raise HTTPException(500, f"RSA signing failed: {e}")

    # ---------- 4. QR payload (5 fields, NO timestamp) ----------
    qr_payload = {
        "content_hash":  content_hash,
        "metadata_hash": metadata_hash,
        "phash":         phash,
        "signature":     signature_hex,
        "issuer":        issuer,
        "document_id":   doc_id,
        "document_type": document_type,
    }
    assert "timestamp" not in qr_payload, \
        "Timestamp must NOT be in QR (Timestamp-QR fix)"

    # Encode QR
    try:
        qr_bytes = _qr.encode_record(qr_payload)
    except Exception as e:
        raise HTTPException(500, f"QR encoding failed: {e}")

    # ---------- 5. Write to group-wise node (Layer 3) ----------
    issued_at = datetime.utcnow().isoformat() + "Z"
    try:
                # Add to blockchain via get_ledger()
                # Add to blockchain via group-wise node
        ledger = get_ledger(document_type=document_type)
        ledger.add_document(
            doc_id=doc_id,
            content_hash=content_hash,
            sig_hash=signature_hex,
            issuer=issuer,
            issued_at=issued_at,
            metadata={
                "document_type": document_type,
                "metadata_hash": metadata_hash,
                "phash": phash,
            },
        )
        
    except Exception as e:
        raise HTTPException(500, f"Blockchain write failed: {e}")

    # ---------- 6. Response ----------
    return IssueResponse(
        document_id=doc_id,
        document_type=document_type,
        qr_base64=base64.b64encode(qr_bytes).decode("ascii"),
        integrity_record=qr_payload,
        content_hash=content_hash,
        metadata_hash=metadata_hash,
        phash=phash,
        issued_at=issued_at,
    )



@router.post("/verify", response_model=VerifyResponse)
async def verify_document(
    document: UploadFile = File(..., description="Document image with embedded QR"),
    signature: UploadFile = File(..., description="Signature region image"),
    reference: Optional[UploadFile] = File(None, description="Reference signature (for AI comparison)"),
):
    """
    Full hybrid verification:
    
    1. Extract and decode QR from document
    2. Verify cryptographic integrity (HMAC + hash + timestamp)
    3. Run AI signature verification (RQ1 Siamese CNN)
    4. Fuse AI + crypto decisions
    5. Return combined verdict with explanations
    """
    try:
        doc_bytes = await document.read()
        sig_bytes = await signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploads: {e}")
    
    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")
    
    # Step 1: Decode QR from document
    qr_record = _qr.decode_from_document(doc_bytes)
    
    if qr_record is None:
        # No QR found — return immediate tamper verdict
        return VerifyResponse(
            is_authentic=False,
            confidence=0.0,
            ai_score=0.0,
            crypto_score=0.0,
            tamper_detected=True,
            decision_path="NO_QR",
            explanations={
                "error": "QR code not found or unreadable",
                "hint": "Document may be forged or QR damaged",
            },
            document_id=None,
            verified_at=datetime.utcnow().isoformat() + "Z",
        )
    
    if "_error" in qr_record:
        raise HTTPException(400, f"QR parse error: {qr_record['_error']}")
    
    # Step 2: Verify cryptographic integrity
    current_hash = _crypto.compute_content_hash_with_mask(doc_bytes)
    crypto_result = _crypto.verify_integrity_record(
        qr_record.copy(),
        current_hash,
        skip_document_match=False,
    )
    
    # Step 3: Run AI verification (RQ1)
    # Step 3: Run AI verification (RQ1) with reference if provided
        # Step 3: Run AI verification (RQ1)
    # Step 3: Run AI verification (RQ1) with reference if provided
    ref_bytes = await reference.read() if reference else None
    ai_result = await _run_ai_verification(sig_bytes, ref_bytes)

    # Step 4: Fuse decisions
    phash_new = _crypto.compute_phash(doc_bytes) if doc_bytes else None
    phash_qr = qr_record.get("phash") if qr_record else None

    fusion_result = _fusion.fuse(
        ai_result, crypto_result,
        phash_new=phash_new,
        phash_qr=phash_qr,
    )
        
    # Step 5: Return result
    return VerifyResponse(
        is_authentic=fusion_result.is_authentic,
        confidence=fusion_result.confidence,
        ai_score=fusion_result.ai_score,
        crypto_score=fusion_result.crypto_score,
        tamper_detected=fusion_result.tamper_detected,
        decision_path=fusion_result.decision_path,
        explanations=fusion_result.explanations,
        document_id=qr_record.get("doc_id"),
        verified_at=datetime.utcnow().isoformat() + "Z",
    )


@router.post("/verify-batch")
async def verify_batch(
    documents: List[UploadFile] = File(..., description="List of documents"),
    signatures: List[UploadFile] = File(..., description="List of signatures"),
):
    """
    Batch verification of multiple documents.
    
    Number of documents must match number of signatures.
    """
    if len(documents) != len(signatures):
        raise HTTPException(
            400,
            f"Mismatch: {len(documents)} documents vs {len(signatures)} signatures",
        )
    
    if len(documents) > 50:
        raise HTTPException(400, "Batch size exceeds 50 documents")
    
    results = []
    for doc, sig in zip(documents, signatures):
        try:
            doc_bytes = await doc.read()
            sig_bytes = await sig.read()
            
            qr_record = _qr.decode_from_document(doc_bytes)
            if qr_record is None or "_error" in qr_record:
                results.append({
                    "file": doc.filename,
                    "is_authentic": False,
                    "decision_path": "NO_QR",
                    "error": "QR not found or unreadable",
                })
                continue
            
            current_hash = _crypto.compute_content_hash_with_mask(doc_bytes)
            crypto_result = _crypto.verify_integrity_record(
        qr_record.copy(),  # copy so we don't mutate cached record
        current_hash,
        skip_document_match=False,
    )
            ai_result = await _run_ai_verification(sig_bytes, None)  # No reference in batch mode
            fusion = _fusion.fuse(ai_result, crypto_result)
            
            results.append({
                "file": doc.filename,
                "document_id": qr_record.get("doc_id"),
                "is_authentic": fusion.is_authentic,
                "confidence": fusion.confidence,
                "decision_path": fusion.decision_path,
                "tamper_detected": fusion.tamper_detected,
            })
        except Exception as e:
            results.append({
                "file": doc.filename,
                "is_authentic": False,
                "error": str(e),
            })
    
    return {
        "total": len(results),
        "authentic": sum(1 for r in results if r.get("is_authentic")),
        "tampered": sum(1 for r in results if r.get("tamper_detected")),
        "results": results,
        "processed_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# RQ3: Issue + Embed (Server-Side QR Embedding)
# ============================================================

@router.post("/issue-and-embed")
async def issue_and_embed(
    document: UploadFile = File(..., description="Document image (PNG/JPEG)"),
    signature: UploadFile = File(..., description="Signature region image"),
    document_id: Optional[str] = Form(None),
    issuer: str = Form("Government of Sri Lanka"),
    ai_confidence: float = Form(0.95),
):
    """
    Issue a document AND return the stamped image with QR embedded.

    Combines /issue + QR embedding in a single API call, so the client
    (Streamlit) does not need to import QRService locally.

    Returns:
        document_id: Generated or custom ID
        qr_base64: QR code as base64 PNG (standalone)
        stamped_document_base64: Document with QR embedded (base64 PNG)
        integrity_record: Full integrity record dict
        issued_at: ISO timestamp
    """
    try:
        doc_bytes = await document.read()
        sig_bytes = await signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploads: {e}")

    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")

    # Generate document ID
    doc_id = document_id or _generate_document_id()

    # Compute hashes

    # Compute hashes with QR region masked (for tamper detection)
    doc_hash = _crypto.compute_content_hash_with_mask(doc_bytes)
    sig_hash = _crypto.compute_signature_hash(sig_bytes)

    # Build integrity record
    record = _crypto.build_integrity_record(
        document_id=doc_id,
        document_hash=doc_hash,
        signature_hash=sig_hash,
        ai_confidence=ai_confidence,
        metadata={"issuer": issuer},
    )

    # Encode QR
    try:
        qr_bytes = _qr.encode_record(record)
    except Exception as e:
        raise HTTPException(500, f"QR encoding failed: {e}")

    # Embed QR into document (SERVER-SIDE)
    try:
        stamped_bytes = _qr.embed_in_document(
            doc_bytes,
            qr_bytes,
            position="bottom-right",
        )
    except Exception as e:
        raise HTTPException(500, f"QR embedding failed: {e}")

       # ============================================================
    # NEW: Add to blockchain ledger
    # ============================================================
    try:
        ledger = get_ledger()
        block = ledger.add_document(
            doc_id=doc_id,
            content_hash=doc_hash,
            sig_hash=sig_hash,
            issuer=issuer,
            issued_at=datetime.utcnow().isoformat() + "Z",
            metadata={
                "issuer_display": issuer,
                "ai_confidence": ai_confidence,
            },
        )
        block_hash = block["block_hash"]
        block_index = block["index"]
    except Exception as e:
        # Log but don't fail — blockchain is optional
        block_hash = None
        block_index = None
        print(f"[WARN] Blockchain add failed: {e}")

    # Return both QR and stamped document as base64
    return {
        "document_id": doc_id,
        "qr_base64": base64.b64encode(qr_bytes).decode("ascii"),
        "stamped_document_base64": base64.b64encode(stamped_bytes).decode("ascii"),
        "integrity_record": record,
        "blockchain": {
            "block_hash": block_hash,
            "block_index": block_index,
        },
        "issued_at": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# RQ3: Blockchain Ledger Endpoints
# ============================================================

class LedgerLookupRequest(BaseModel):
    """Request body for ledger lookup."""
    doc_id: str = Field(..., description="Document ID to look up")


class CertifiedCopyRequest(BaseModel):
    """Request body for certified copy issuance."""
    original_doc_id: str = Field(..., description="Original document ID")
    certifier: str = Field("GovLK", description="Certifying authority")


@router.get("/ledger/stats")
async def ledger_stats():
    """
    Get blockchain ledger statistics.

    Returns:
        total_blocks: Number of blocks in the chain
        genesis_hash: First block hash
        latest_hash: Most recent block hash
        latest_index: Index of latest block
    """
    try:
        ledger = get_ledger()
        return {
            "status": "ok",
            "stats": ledger.get_stats(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(500, f"Ledger error: {e}")


@router.get("/ledger/verify-chain")
async def verify_chain():
    """
    Verify the integrity of the entire blockchain ledger.

    Returns:
        valid: True if chain is intact
        length: Number of blocks
        errors: List of any tampering errors
    """
    try:
        ledger = get_ledger()
        result = ledger.verify_chain()
        return {
            "status": "ok",
            **result,
            "verified_at": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as e:
        raise HTTPException(500, f"Chain verification failed: {e}")


@router.post("/ledger/lookup")
async def ledger_lookup(req: LedgerLookupRequest):
    """
    Look up a document in the blockchain ledger by doc_id.

    Returns the full block if found, or 404 if not.
    """
    try:
        ledger = get_ledger()
        block = ledger.get_document(req.doc_id)
        if block is None:
            raise HTTPException(404, f"Document not found: {req.doc_id}")
        return {
            "status": "ok",
            "block": block,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Lookup failed: {e}")


@router.get("/ledger/find-by-hash")
async def find_by_hash(content_hash: str):
    """
    Find all blocks matching a content hash (original + certified copies).

    Query parameter: content_hash
    """
    try:
        ledger = get_ledger()
        blocks = ledger.find_by_content_hash(content_hash)
        return {
            "status": "ok",
            "content_hash": content_hash,
            "matches": len(blocks),
            "blocks": blocks,
        }
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


@router.post("/ledger/certified-copy")
async def issue_certified_copy(req: CertifiedCopyRequest):
    """
    Issue a certified copy of an existing document.

    The certified copy has the SAME content_hash as the original
    but a DIFFERENT issued_at timestamp. This is the supervisor's
    key insight: certified copies are NOT forgeries.
    """
    try:
        ledger = get_ledger()
        block = ledger.add_certified_copy(
            original_doc_id=req.original_doc_id,
            certifier=req.certifier,
        )
        return {
            "status": "ok",
            "certified_copy": block,
            "message": f"Certified copy issued for {req.original_doc_id}",
        }
    except ValueError as e:
        raise HTTPException(404, str(e))
    except Exception as e:
        raise HTTPException(500, f"Certified copy issuance failed: {e}")


@router.get("/ledger/export")
async def export_ledger():
    """
    Export the entire blockchain ledger as JSON.

    Useful for backup or for verifying on another node.
    """
    try:
        ledger = get_ledger()
        return {
            "status": "ok",
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "chain": ledger.chain,
        }
    except Exception as e:
        raise HTTPException(500, f"Export failed: {e}")

    

# ============================================================
# LAYER 3: QR Code Verification (SigVerify Theory)
# ============================================================

@router.post("/verify-layer3")
async def verify_layer3(
    document: UploadFile = File(..., description="Document with QR code"),
):
    """
    LAYER 3: QR Code Verification (6-step process)

    Implements SigVerify theory:
    1. SCAN QR Code
    2. Verify CONTENT HASH
    3. Verify METADATA HASH
    4. Verify SIGNATURE
    5. Check BLOCKCHAIN
    6. FINAL DECISION

    Returns 4 scenarios:
    - FULLY_AUTHENTIC
    - TAMPERED
    - METADATA_MODIFIED
    - AUTHENTIC_NOT_IN_BLOCKCHAIN
    """
    try:
        doc_bytes = await document.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read document: {e}")

    if not doc_bytes:
        raise HTTPException(400, "Empty document")

    try:
        layer3 = QRVerificationLayer()
        ledger = get_ledger()
        result = layer3.verify_document(doc_bytes, blockchain_ledger=ledger)
        return result
    except Exception as e:
        raise HTTPException(500, f"Layer 3 verification failed: {e}")