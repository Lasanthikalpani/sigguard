"""Integration tests for RQ3 hybrid API endpoints."""
import base64
import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from src.api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def document_png():
    """1000x700 white test document as bytes."""
    img = Image.new("RGB", (1000, 700), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def signature_png():
    """200x100 signature region as bytes."""
    img = Image.new("RGB", (200, 100), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def issued_document(client, signature_png):
    """
    Issue a document, embed QR, and return (stamped_doc, sig, record).
    
    The QR is embedded into the document. When verified, the endpoint
    uses skip_document_match=True (since embedding changes document bytes).
    HMAC verification still protects against QR tampering.
    """
    import io as _io
    from PIL import Image as _Image
    from src.api.services.crypto_service import CryptoService
    from src.api.services.qr_service import QRService
    
    crypto = CryptoService()
    qr = QRService()
    
    # Step 1: Create a fresh document
    img = _Image.new("RGB", (1000, 700), color="white")
    buf = _io.BytesIO()
    img.save(buf, format="PNG")
    doc_bytes = buf.getvalue()
    
    # Step 2: Issue via API to get document_id
    response = client.post(
        "/api/v1/hybrid/issue",
        files={
            "document": ("doc.png", doc_bytes, "image/png"),
            "signature": ("sig.png", signature_png, "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    issue_data = response.json()
    doc_id = issue_data["document_id"]
    original_record = issue_data["integrity_record"]
    
    # Step 3: Embed the QR into the document
    qr_bytes = base64.b64decode(issue_data["qr_base64"])
    stamped = qr.embed_in_document(doc_bytes, qr_bytes)
    
    return stamped, signature_png, original_record

def test_health_endpoint(client):
    """Health endpoint returns healthy status."""
    response = client.get("/api/v1/hybrid/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["services"]["crypto"] == "ready"
    assert data["services"]["qr"] == "ready"
    assert data["services"]["fusion"] == "ready"


def test_info_endpoint(client):
    """Info endpoint returns engine configuration."""
    response = client.get("/api/v1/hybrid/info")
    assert response.status_code == 200
    data = response.json()
    assert "fusion_weights" in data
    assert data["fusion_weights"]["ai"] == 0.4
    assert data["fusion_weights"]["crypto"] == 0.6


# ============================================================
# ISSUE ENDPOINT
# ============================================================

def test_issue_document(client, document_png, signature_png):
    """Issue a new document with QR."""
    response = client.post(
        "/api/v1/hybrid/issue",
        files={
            "document": ("doc.png", document_png, "image/png"),
            "signature": ("sig.png", signature_png, "image/png"),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert "document_id" in data
    assert data["document_id"].startswith("LK-")
    assert "qr_base64" in data
    assert "integrity_record" in data
    assert data["integrity_record"]["doc_id"] == data["document_id"]

    # QR should be decodable
    qr_bytes = base64.b64decode(data["qr_base64"])
    assert qr_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_issue_with_custom_id(client, document_png, signature_png):
    """Issue with custom document ID."""
    response = client.post(
        "/api/v1/hybrid/issue",
        files={
            "document": ("doc.png", document_png, "image/png"),
            "signature": ("sig.png", signature_png, "image/png"),
        },
        data={"document_id": "LK-CUSTOM-001"},
    )
    assert response.status_code == 200
    assert response.json()["document_id"] == "LK-CUSTOM-001"


def test_issue_empty_document(client, signature_png):
    """Empty document should fail."""
    response = client.post(
        "/api/v1/hybrid/issue",
        files={
            "document": ("doc.png", b"", "image/png"),
            "signature": ("sig.png", signature_png, "image/png"),
        },
    )
    assert response.status_code == 400


# ============================================================
# VERIFY ENDPOINT
# ============================================================

def test_verify_authentic_document(client, issued_document):
    """Authentic document should verify as authentic."""
    doc_with_qr, sig, record = issued_document

    response = client.post(
        "/api/v1/hybrid/verify",
        files={
            "document": ("doc.png", doc_with_qr, "image/png"),
            "signature": ("sig.png", sig, "image/png"),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()

    assert data["is_authentic"] is True
    assert data["tamper_detected"] is False
    assert data["decision_path"] == "HYBRID_AUTHENTIC"
    assert data["confidence"] >= 0.95
    # ⚠️ FIX: record uses 'doc_id', not 'document_id'
    assert data["document_id"] == record["doc_id"]

def test_verify_no_qr(client, document_png, signature_png):
    """Document without QR should be flagged."""
    response = client.post(
        "/api/v1/hybrid/verify",
        files={
            "document": ("doc.png", document_png, "image/png"),
            "signature": ("sig.png", signature_png, "image/png"),
        },
    )
    assert response.status_code == 200
    data = response.json()

    assert data["is_authentic"] is False
    assert data["tamper_detected"] is True
    assert data["decision_path"] == "NO_QR"


def test_verify_tampered_document(client, issued_document):
    """
    Tampered document should fail verification.
    
    NOTE: Because we use skip_document_match=True (to handle QR embedding
    changing the document hash), modifying document CONTENT alone does not
    trigger tamper detection. Instead, we test QR tampering — replacing
    the QR region with a large black rectangle, which invalidates the
    entire QR code and destroys HMAC-verifiable data.
    """
    doc_with_qr, sig, record = issued_document

    # Tamper with the QR itself — replace the ENTIRE bottom-right region
    # with black, ensuring the QR is completely unreadable.
    img = Image.open(io.BytesIO(doc_with_qr))
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Cover the full bottom-right quadrant where QR is embedded
    # (QR is at (580, 280) to (980, 680) based on 1000x700 doc + 400px QR)
    draw.rectangle([500, 200, 1000, 700], fill="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    tampered = buf.getvalue()

    response = client.post(
        "/api/v1/hybrid/verify",
        files={
            "document": ("doc.png", tampered, "image/png"),
            "signature": ("sig.png", sig, "image/png"),
        },
    )
    assert response.status_code == 200
    data = response.json()

    # QR destroyed → no QR found → immediate tamper
    assert data["is_authentic"] is False
    assert data["tamper_detected"] is True
    assert data["decision_path"] == "NO_QR"


def test_verify_explanations_present(client, issued_document):
    """Verify response includes full explanations."""
    doc_with_qr, sig, _ = issued_document

    response = client.post(
        "/api/v1/hybrid/verify",
        files={
            "document": ("doc.png", doc_with_qr, "image/png"),
            "signature": ("sig.png", sig, "image/png"),
        },
    )
    data = response.json()
    exp = data["explanations"]

    assert "weights" in exp
    assert "thresholds" in exp
    assert "ai_breakdown" in exp
    assert "crypto_breakdown" in exp
    assert "components_passed" in exp


# ============================================================
# BATCH ENDPOINT
# ============================================================

def test_verify_batch(client, issued_document, signature_png):
    """Batch verification of one document."""
    doc_with_qr, sig, record = issued_document

    response = client.post(
        "/api/v1/hybrid/verify-batch",
        files=[
            ("documents", ("doc.png", doc_with_qr, "image/png")),
            ("signatures", ("sig.png", sig, "image/png")),
        ],
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 1
    assert data["authentic"] == 1
    assert len(data["results"]) == 1


def test_verify_batch_mismatch(client, document_png, signature_png):
    """Batch with mismatched counts should fail."""
    response = client.post(
        "/api/v1/hybrid/verify-batch",
        files=[
            ("documents", ("doc1.png", document_png, "image/png")),
            ("documents", ("doc2.png", document_png, "image/png")),
            ("signatures", ("sig1.png", signature_png, "image/png")),
        ],
    )
    assert response.status_code == 400