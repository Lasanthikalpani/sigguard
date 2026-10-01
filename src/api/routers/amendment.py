"""
RQ3 Layer 5: Document Amendment API Router.

Endpoints:
  POST /api/v1/amendment/amend           — issue an amendment
  POST /api/v1/amendment/verify          — verify an (possibly amended) doc
  GET  /api/v1/amendment/lineage/{doc_id} — full lineage of a document
  GET  /api/v1/amendment/reasons         — list supported amendment reasons
  GET  /api/v1/amendment/health          — service health
"""
import base64
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel, Field

from src.api.services.amendment_service import AmendmentService
from src.api.services.blockchain_service import get_ledger


router = APIRouter(
    prefix="/api/v1/amendment",
    tags=["RQ3 Layer 5 - Amendment"],
)

_amendment = None


def _get_service() -> AmendmentService:
    global _amendment
    if _amendment is None:
        _amendment = AmendmentService(ledger=get_ledger())
    return _amendment


# ============================================================
# MODELS
# ============================================================

class LineageResponse(BaseModel):
    doc_id: str
    lineage_length: int
    lineage: list


class ReasonsResponse(BaseModel):
    supported: dict


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "amendment",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/reasons", response_model=ReasonsResponse)
async def list_reasons():
    """List supported amendment reasons."""
    return ReasonsResponse(supported=AmendmentService.SUPPORTED_REASONS)


@router.post("/amend")
async def amend_document(
    original_doc_id: str = Form(..., description="ID of the original document"),
    amendment_reason: str = Form(..., description="e.g. 'surname_change'"),
    new_document: UploadFile = File(..., description="New document content (PNG/JPEG)"),
    new_signature: UploadFile = File(..., description="New signature region"),
    evidence_json: Optional[str] = Form(None, description="Optional JSON evidence"),
    issuer: str = Form("Registrar General's Office"),
):
    """
    Issue an amended document (Layer 5).

    Returns the amended document ID, new QR, new integrity record,
    and blockchain lineage info.
    """
    import json
    svc = _get_service()

    try:
        new_doc_bytes = await new_document.read()
        new_sig_bytes = await new_signature.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read uploads: {e}")

    if not new_doc_bytes or not new_sig_bytes:
        raise HTTPException(400, "Empty document or signature")

    evidence = None
    if evidence_json:
        try:
            evidence = json.loads(evidence_json)
        except json.JSONDecodeError as e:
            raise HTTPException(400, f"Invalid evidence_json: {e}")

    try:
        result = svc.issue_amendment(
            original_doc_id=original_doc_id,
            new_content_bytes=new_doc_bytes,
            new_signature_bytes=new_sig_bytes,
            amendment_reason=amendment_reason,
            evidence=evidence,
            issuer=issuer,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Amendment failed: {e}")


@router.post("/verify")
async def verify_amendment(
    document: UploadFile = File(..., description="Document to verify (PNG/JPEG)"),
):
    """
    Verify an (possibly amended) document.

    Returns one of:
      FULLY_AUTHENTIC       — original document, all checks pass
      AMENDED_AUTHENTIC     — amendment recognized, lineage verified
      TAMPERED              — content hash mismatch / HMAC invalid
      QR_MISSING            — no QR found
    """
    svc = _get_service()
    try:
        doc_bytes = await document.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read document: {e}")

    if not doc_bytes:
        raise HTTPException(400, "Empty document")

    try:
        result = svc.verify_amendment(doc_bytes)
        # Convert lineage blocks to JSON-safe (they already are)
        return result
    except Exception as e:
        raise HTTPException(500, f"Verification failed: {e}")


@router.get("/lineage/{doc_id}", response_model=LineageResponse)
async def get_lineage(doc_id: str):
    """Return the full lineage (original → amendments) for a document."""
    svc = _get_service()
    try:
        result = svc.get_lineage(doc_id)
        return LineageResponse(**result)
    except Exception as e:
        raise HTTPException(500, f"Lineage lookup failed: {e}")