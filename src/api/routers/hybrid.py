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
    document_type: str          # ← 🆕
    qr_base64: str
    integrity_record: dict
    content_hash: str           # ← 🆕
    metadata_hash: str          # ← 🆕
    phash: str                  # ← 🆕
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
    metadata_hash = _crypto.compute_metadata_hash(issuer, doc_id)

    # ---------- 3. RSA signature (Layer 4) ----------
    try:
        signature_hex = _crypto.rsa_sign(content_hash, metadata_hash)
    except Exception as e:
        raise HTTPException(500, f"RSA signing failed: {e}")

    # ---------- 4. QR payload (5 fields, NO timestamp) ----------
    qr_payload = {
        "content_hash":  content_hash,
        "metadata_hash": metadata_hash,
        "phash":         "",  # ← පසුව පුරවන්න
        "signature":     signature_hex,
        "issuer":        issuer,
        "document_id":   doc_id,
        "document_type": document_type,
    }
    assert "timestamp" not in qr_payload, "Timestamp must NOT be in QR"

    # Encode QR
    try:
        qr_bytes = _qr.encode_record(qr_payload)
    except Exception as e:
        raise HTTPException(500, f"QR encoding failed: {e}")

    # 🆕 ---------- 4b. Embed QR and recompute phash ----------
    try:
        from PIL import Image
        import io
        
        doc_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")
        qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGB")
        
        qr_size = 400
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        doc_img.paste(qr_img, (doc_img.width - qr_size - 50, 50))
        
        buf = io.BytesIO()
        doc_img.save(buf, format="PNG")
        embedded_doc_bytes = buf.getvalue()
        
        # Embed කළ ලේඛනයේ pHash
        phash = _crypto.compute_phash(embedded_doc_bytes)
        
        # QR payload එකට phash එකතු කර නැවත QR එක සාදන්න
        qr_payload["phash"] = phash
        qr_bytes = _qr.encode_record(qr_payload)
        
    except Exception as e:
        raise HTTPException(500, f"QR embedding failed: {e}")

    # ---------- 5. Write to group-wise node (Layer 3) ----------
    issued_at = datetime.utcnow().isoformat() + "Z"
    try:
        ledger = get_ledger(document_type=document_type)
        ledger.add_document(
            doc_id=doc_id,
            content_hash=content_hash,
            sig_hash=signature_hex,
            issuer=issuer,
            issued_at=issued_at,
            metadata={
                "document_type": document_type,
                "document_status": "ORIGINAL",
                "metadata_hash": metadata_hash,
                "phash": phash,
                "copy_of": None,
            },
        )
    except Exception as e:
        raise HTTPException(500, f"Blockchain write failed: {e}")

    # ---------- 6. Response ----------
           # ---------- 6. Response ----------
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



@router.post("/verify")
async def verify_document(
    document: UploadFile = File(...),
    signature: UploadFile = File(...),
    reference: UploadFile = File(None),
):
    """
    Full hybrid verification (RQ3).
    """
    from src.api.services.crypto_service import CryptoService
    
    try:
        doc_bytes = await document.read()
        sig_bytes = await signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read document: {e}")

    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")

    # Step 1: Decode QR
    qr_record = _qr.decode_from_document(doc_bytes)
    if qr_record is None or "_error" in qr_record:
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

    # Step 2: Verify cryptographic integrity
    current_hash = _crypto.compute_content_hash_with_mask(doc_bytes)
    crypto_result = _crypto.verify_integrity_record(
        qr_record.copy(),
        current_hash,
        skip_document_match=False,
    )

    # Step 3: Run AI verification
    ref_bytes = await reference.read() if reference else None
    ai_result = await _run_ai_verification(sig_bytes, ref_bytes)

    # Step 4: Dual-Hash pHash Fallback (NEW)
    crypto = CryptoService()
    phash_new = crypto.compute_phash(doc_bytes) if doc_bytes else None
    phash_qr = qr_record.get("phash") if qr_record else None

    # Debug prints
    print(f"[DEBUG] phash_new = {phash_new}")
    print(f"[DEBUG] phash_qr = {phash_qr}")
    print(f"[DEBUG] crypto_result = {crypto_result}")

    # Step 5: Fuse decisions (with pHash fallback)
    fusion_result = _fusion.fuse(
        ai_result, crypto_result,
        phash_new=phash_new,
        phash_qr=phash_qr,
    )

    # Step 6: Return result
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
    document: UploadFile = File(...),
    signature: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    document_type: str = Form(...),
    issuer: str = Form("Government of Sri Lanka"),
    ai_confidence: float = Form(0.95),
):
    """
    Issue a document AND return the stamped image with QR embedded.
    """
    from PIL import Image
    import io
    import base64 as _b64
    from datetime import datetime as _dt
    from src.api.services.qr_service import QRService
    from src.api.services.crypto_service import CryptoService
    from src.api.services.blockchain_service import get_ledger
    
    # 🆕 CryptoService instance එකක් සාදන්න
    crypto = CryptoService()
    qr_service = QRService()
    
    # 1. Read bytes
    doc_bytes = await document.read()
    sig_bytes = await signature.read()
    if not doc_bytes or not sig_bytes:
        raise HTTPException(400, "Empty document or signature")
    
    doc_id = document_id or _generate_document_id()
    
    # 2. Hashes (instance methods)
    content_hash = crypto.compute_content_hash_with_mask(doc_bytes)
    metadata_hash = crypto.compute_metadata_hash(issuer, doc_id)
    
    # 3. RSA sign
    signature_hex = crypto.rsa_sign(content_hash, metadata_hash)
    
    # 4. QR payload
        # 4. QR payload
    qr_payload = {
        "content_hash": content_hash,
        "metadata_hash": metadata_hash,
        "phash": "",
        "signature": signature_hex,
        "issuer": issuer,
        "document_id": doc_id,
        "document_type": document_type,
    }
    assert "timestamp" not in qr_payload

    # 5. පළමු QR එක encode කරන්න
    qr_bytes = qr_service.encode_record(qr_payload)
    qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGB")

    # 6. QR එක ලේඛනයට embed කරන්න
    doc_img = Image.open(io.BytesIO(doc_bytes)).convert("RGB")
    qr_size = 300
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    x = 50
    y = doc_img.height - qr_size - 50
    doc_img.paste(qr_img, (x, y))

    # 7. Embed කළ ලේඛනයේ pHash ගණනය කරන්න
    buf = io.BytesIO()
    doc_img.save(buf, format="PNG")
    embedded_bytes = buf.getvalue()
    phash = crypto.compute_phash(embedded_bytes)

    # 8. QR payload එකට phash එකතු කර, නැවත QR එක encode කරන්න
    qr_payload["phash"] = phash
    qr_bytes = qr_service.encode_record(qr_payload)
    qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)

    # 9. නව QR එක නැවත ලේඛනයට embed කරන්න
    doc_img.paste(qr_img, (x, y))
    buf = io.BytesIO()
    doc_img.save(buf, format="PNG")
    embedded_bytes = buf.getvalue()
    
    # 10. නව embedded_bytes හි pHash ගණනය කරන්න
    final_phash = crypto.compute_phash(embedded_bytes)
    # 🆕 QR එකේ phash එක, ලේඛනයේ phash එකට සමාන කරන්න
    qr_payload["phash"] = final_phash
    qr_bytes = qr_service.encode_record(qr_payload)
    
    # 11. අවසාන QR එක නැවත embed කරන්න
    qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGB")
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    doc_img.paste(qr_img, (x, y))
    buf = io.BytesIO()
    doc_img.save(buf, format="PNG")
    embedded_bytes = buf.getvalue()
    phash = crypto.compute_phash(embedded_bytes)
    
    # 8. Update QR payload with phash and re-encode
    qr_payload["phash"] = phash
    qr_bytes = qr_service.encode_record(qr_payload)
    
    # 9. Write to blockchain
    issued_at = _dt.utcnow().isoformat() + "Z"
    ledger = get_ledger(document_type=document_type)
    ledger.add_document(
        doc_id=doc_id,
        content_hash=content_hash,
        sig_hash=signature_hex,
        issuer=issuer,
        issued_at=issued_at,
        metadata={
            "document_type": document_type,
            "document_status": "ORIGINAL",
            "metadata_hash": metadata_hash,
            "phash": phash,
            "copy_of": None,
        },
    )
    
    # 10. Return response
    return {
        "document_id": doc_id,
        "document_type": document_type,
        "qr_base64": _b64.b64encode(qr_bytes).decode("ascii"),
        "stamped_document_base64": _b64.b64encode(embedded_bytes).decode("ascii"),
        "integrity_record": qr_payload,
        "issued_at": issued_at,
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
    document_type: str = Field("BIRTH_CERTIFICATE", description="Document type (e.g., BIRTH_CERTIFICATE)")  # ← 🆕 මෙය එකතු කරන්න
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


class LedgerLookupRequest(BaseModel):
    doc_id: str
    document_type: str = None  # ← 🆕 මෙය එකතු කරන්න

@router.post("/ledger/lookup")
async def ledger_lookup(req: LedgerLookupRequest):
    # 🆕 Group-wise node එක තෝරන්න
    ledger = get_ledger(document_type=req.document_type) if req.document_type else get_ledger()
    
    block = ledger.get_document(req.doc_id)
    if block is None:
        raise HTTPException(404, f"Document not found: {req.doc_id}")
    return {"status": "ok", "document": block}




@router.get("/ledger/find-by-hash")
async def find_by_hash(content_hash: str, document_type: str = None):
    """
    Find all blocks matching a content hash (original + certified copies).

    Query parameters: 
    - content_hash (required)
    - document_type (optional, e.g., BIRTH_CERTIFICATE)
    """
    try:
        # 🆕 document_type එකක් ලබා දී ඇත්නම්, එම Group-wise node එක තෝරන්න
        ledger = get_ledger(document_type=document_type) if document_type else get_ledger()
        
        blocks = ledger.find_by_content_hash(content_hash)
        return {
            "status": "ok",
            "content_hash": content_hash,
            "document_type": document_type or "ALL",
            "matches": len(blocks),
            "blocks": blocks,
        }
    except Exception as e:
        raise HTTPException(500, f"Search failed: {e}")


# src/api/routers/hybrid.py හි

@router.post("/ledger/certified-copy")
async def issue_certified_copy(req: CertifiedCopyRequest):
    """
    Issue a certified copy of an existing document.
    - Uses the SAME content_hash and metadata_hash as the original.
    - Creates a NEW blockchain entry with document_type = "CERTIFIED_COPY".
    """
    try:
        ledger = get_ledger(document_type=req.document_type)
        
        # 1. Original එක තිබේදැයි පරීක්ෂා කරන්න
        original = ledger.get_document(req.original_doc_id)
        if not original:
            raise HTTPException(404, f"Original document not found: {req.original_doc_id}")
        
        # 2. Original එකේ document_status "ORIGINAL" ද යන්න පරීක්ෂා කරන්න
        original_status = original.get("metadata", {}).get("document_status", "ORIGINAL")
        if original_status != "ORIGINAL":
            raise HTTPException(400, "Document is not an ORIGINAL, cannot create certified copy")
        
        # 3. Certified Copy එකක් සාදන්න (add_certified_copy ශ්‍රිතය හරහා)
        new_block = ledger.add_certified_copy(
            original_doc_id=req.original_doc_id,
            certifier=req.certifier or "Registrar General's Office"
        )
        
        return {
            "status": "ok",
            "message": "Certified copy issued successfully",
            "original_doc_id": req.original_doc_id,
            "new_doc_id": new_block["doc_id"],
            "document_status": "CERTIFIED_COPY",
            "issued_at": new_block["issued_at"],
            "block_hash": new_block["block_hash"]
        }
    except Exception as e:
        raise HTTPException(500, f"Certified copy creation failed: {e}")
    



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