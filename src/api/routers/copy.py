"""
RQ3 Layer 6: Copy vs Original API Router.

Endpoints:
  POST /api/v1/copy/issue-certified   — issue a registry-certified copy
  POST /api/v1/copy/classify          — classify a document (original/copy/etc.)
  GET  /api/v1/copy/health            — service health
  GET  /api/v1/copy/types             — list supported document types
"""
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from pydantic import BaseModel

from src.api.services.copy_service import CopyService
from src.api.services.blockchain_service import get_ledger


router = APIRouter(
    prefix="/api/v1/copy",
    tags=["RQ3 Layer 6 - Copy vs Original"],
)

_service = None


def _get_service() -> CopyService:
    global _service
    if _service is None:
        _service = CopyService(ledger=get_ledger())
    return _service


# ============================================================
# MODELS
# ============================================================

class TypesResponse(BaseModel):
    supported: dict


# ============================================================
# ENDPOINTS
# ============================================================

@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "copy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@router.get("/types", response_model=TypesResponse)
async def list_types():
    """List all document types that Layer 6 can classify."""
    return TypesResponse(supported={
        "ORIGINAL": "Registry-issued original document",
        "CERTIFIED_COPY": "Registry-issued certified copy (new QR, new timestamp)",
        "PHOTOCOPY": "Simple photocopy (original QR, same timestamp)",
        "AMENDMENT": "Legitimate amendment (new QR, new content)",
        "TAMPERED": "Content or QR has been modified",
        "QR_MISSING": "No QR code found",
        "UNKNOWN": "QR valid but could not be classified",
    })


@router.post("/issue-certified")
async def issue_certified_copy(
    original_doc_id: str = Form(..., description="ID of the original document"),
    certifier: str = Form("Registrar General's Office"),
    reason: str = Form("certified_copy_request"),
):
    """
    Issue a registry-certified copy of an existing document.

    The certified copy has:
      - SAME content hash
      - NEW timestamp
      - NEW QR code
      - Blockchain entry with is_certified_copy=True
    """
    svc = _get_service()
    try:
        result = svc.issue_certified_copy(
            original_doc_id=original_doc_id,
            certifier=certifier,
            reason=reason,
        )
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Certified copy issuance failed: {e}")


@router.post("/classify")
async def classify_document(
    document: UploadFile = File(..., description="Document to classify (PNG/JPEG)"),
):
    """
    Classify a document as ORIGINAL, CERTIFIED_COPY, PHOTOCOPY,
    AMENDMENT, or TAMPERED.

    Returns the document type and an explanation.
    """
    svc = _get_service()
    try:
        doc_bytes = await document.read()
    except Exception as e:
        raise HTTPException(400, f"Failed to read document: {e}")

    if not doc_bytes:
        raise HTTPException(400, "Empty document")

    try:
        result = svc.classify_document(doc_bytes)
        return result
    except Exception as e:
        raise HTTPException(500, f"Classification failed: {e}")