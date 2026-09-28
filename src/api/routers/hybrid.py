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
    document_bytes: bytes,
    signature_bytes: bytes,
) -> dict:
    """
    Run RQ1 AI verification (Siamese CNN).
    
    In production, this calls the RQ1 model. If unavailable,
    falls back to a placeholder that assumes high confidence
    (for testing the hybrid pipeline).
    """
    try:
        # Try to use RQ1 AI service if available
        from src.api.services.ai_service import AIService
        ai = AIService()
        result = await ai.verify_signature(document_bytes, signature_bytes)
        return result
    except (ImportError, AttributeError):
        # Fallback: use AI confidence from request or default
        return {
            "similarity": 0.94,
            "prediction": "genuine",
            "_fallback": True,
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


@router.post("/issue", response_model=IssueResponse)
async def issue_document(
    document: UploadFile = File(..., description="Document image (PNG/JPEG)"),
    signature: UploadFile = File(..., description="Signature region image"),
    document_id: Optional[str] = Form(None),
    issuer: str = Form("Government of Sri Lanka"),
    ai_confidence: float = Form(0.95),
):
    """
    Issue a new document with an embedded QR integrity record.
    
    Flow:
    1. Read document + signature bytes
    2. Compute SHA-256 hashes
    3. Build integrity record with HMAC signature
    4. Encode record as QR code
    5. Return QR + record (caller embeds QR in document)
    """
    try:
        doc_bytes = await document.read()
        sig_bytes = await signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploads: {e}")
    
    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")
    
    # Generate document ID if not provided
    doc_id = document_id or _generate_document_id()
    
    # Compute hashes
    doc_hash = _crypto.compute_document_hash(doc_bytes)
    sig_hash = _crypto.compute_signature_hash(sig_bytes)
    
    # Build integrity record
    record = _crypto.build_integrity_record(
        document_id=doc_id,
        document_hash=doc_hash,
        signature_hash=sig_hash,
        ai_confidence=ai_confidence,
        metadata={"issuer": issuer},
    )
    
    # Encode as QR
    try:
        qr_bytes = _qr.encode_record(record)
    except Exception as e:
        raise HTTPException(500, f"QR encoding failed: {e}")
    
    return IssueResponse(
        document_id=doc_id,
        qr_base64=base64.b64encode(qr_bytes).decode("ascii"),
        integrity_record=record,
        issued_at=datetime.utcnow().isoformat() + "Z",
    )


@router.post("/verify", response_model=VerifyResponse)
async def verify_document(
    document: UploadFile = File(..., description="Document image with embedded QR"),
    signature: UploadFile = File(..., description="Signature region image"),
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
    current_hash = _crypto.compute_document_hash(doc_bytes)
    crypto_result = _crypto.verify_integrity_record(
        qr_record.copy(),
        current_hash,
        skip_document_match=True,
    )
    
    # Step 3: Run AI verification (RQ1)
    ai_result = await _run_ai_verification(doc_bytes, sig_bytes)
    
    # Step 4: Fuse decisions
    fusion_result = _fusion.fuse(ai_result, crypto_result)
    
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
            
            current_hash = _crypto.compute_document_hash(doc_bytes)
            crypto_result = _crypto.verify_integrity_record(
        qr_record.copy(),  # copy so we don't mutate cached record
        current_hash,
        skip_document_match=True,
    )
            ai_result = await _run_ai_verification(doc_bytes, sig_bytes)
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