"""Unit tests for RQ3 QRService."""
import base64
import json
from io import BytesIO

import pytest
from PIL import Image

from src.api.services.qr_service import QRService
from src.api.services.crypto_service import CryptoService


@pytest.fixture
def qr():
    return QRService()


@pytest.fixture
def crypto():
    return CryptoService(secret_key="test-qr-secret")


@pytest.fixture
def sample_record(crypto):
    doc_hash = crypto.compute_document_hash(b"sample document bytes")
    sig_hash = crypto.compute_signature_hash(b"sample signature bytes")
    return crypto.build_integrity_record(
        document_id="LK-TEST-001",
        document_hash=doc_hash,
        signature_hash=sig_hash,
        ai_confidence=0.94,
        metadata={"issuer": "Government of Sri Lanka"},
    )


@pytest.fixture
def sample_document_png():
    """Create a 1000x700 white PNG as a realistic test document."""
    img = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ============================================================
# ENCODING / DECODING
# ============================================================

def test_encode_produces_png_bytes(qr, sample_record):
    """Encoding must produce valid PNG bytes."""
    qr_bytes = qr.encode_record(sample_record)
    assert isinstance(qr_bytes, bytes)
    assert len(qr_bytes) > 100
    # Check PNG magic bytes
    assert qr_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_encode_decode_roundtrip(qr, sample_record):
    """Encode then decode must yield identical record."""
    qr_bytes = qr.encode_record(sample_record)
    decoded = qr.decode_record(qr_bytes)
    
    assert decoded is not None
    assert decoded["doc_id"] == sample_record["doc_id"]
    assert decoded["doc_hash"] == sample_record["doc_hash"]
    assert decoded["hmac"] == sample_record["hmac"]


def test_decoded_record_verifies_with_crypto(qr, crypto, sample_record):
    """Decoded record must pass crypto verification."""
    qr_bytes = qr.encode_record(sample_record)
    decoded = qr.decode_record(qr_bytes)
    
    # Extract original document hash from decoded record
    doc_hash = decoded["doc_hash"]
    result = crypto.verify_integrity_record(decoded, doc_hash)
    
    assert result["hmac_valid"] is True
    assert result["document_match"] is True
    assert result["tamper_detected"] is False


def test_decode_invalid_image_returns_none(qr):
    """Non-QR image should return None."""
    img = Image.new("RGB", (100, 100), color="blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    result = qr.decode_record(buf.getvalue())
    assert result is None


def test_decode_empty_bytes_returns_none(qr):
    """Empty bytes should return None."""
    result = qr.decode_record(b"")
    assert result is None


# ============================================================
# DOCUMENT EMBEDDING
# ============================================================

def test_embed_qr_in_document(qr, sample_record, sample_document_png):
    """QR should embed successfully in document."""
    qr_bytes = qr.encode_record(sample_record)
    stamped = qr.embed_in_document(sample_document_png, qr_bytes)
    
    assert isinstance(stamped, bytes)
    assert stamped[:8] == b"\x89PNG\r\n\x1a\n"


def test_embedded_qr_is_decodable(qr, sample_record, sample_document_png):
    """QR embedded in document must be decodable from full document."""
    qr_bytes = qr.encode_record(sample_record)
    stamped = qr.embed_in_document(sample_document_png, qr_bytes)
    
    decoded = qr.decode_from_document(stamped)
    
    assert decoded is not None
    assert decoded["doc_id"] == sample_record["doc_id"]


def test_embed_positions(qr, sample_record, sample_document_png):
    """All 4 positions should work."""
    qr_bytes = qr.encode_record(sample_record)
    
    for pos in ["bottom-right", "bottom-left", "top-right", "top-left"]:
        stamped = qr.embed_in_document(
            sample_document_png, qr_bytes, position=pos
        )
        assert len(stamped) > 0
        decoded = qr.decode_from_document(stamped)
        assert decoded is not None, f"Failed at position {pos}"


# ============================================================
# CAPACITY / LIMITS
# ============================================================

def test_qr_version_estimation(qr, sample_record):
    """Version estimation should return reasonable value."""
    version = qr.estimate_qr_version(sample_record)
    assert 1 <= version <= 40


def test_payload_size_under_limit(qr, crypto):
    """Integrity record must fit within QR capacity."""
    doc_hash = crypto.compute_document_hash(b"x" * 1000)
    sig_hash = crypto.compute_signature_hash(b"y" * 500)
    record = crypto.build_integrity_record(
        document_id="LK-LONG-001",
        document_hash=doc_hash,
        signature_hash=sig_hash,
        ai_confidence=0.99,
        metadata={"issuer": "GovLK", "extra": "test" * 10},
    )
    
    # Payload should be < 950 bytes after base64
    payload = json.dumps(record, separators=(",", ":"), sort_keys=True)
    encoded = base64.b64encode(payload.encode()).decode()
    assert len(encoded) < qr.get_capacity_bytes(), f"Payload too large: {len(encoded)} bytes"


# ============================================================
# DEGRADATION ROBUSTNESS
# ============================================================

def test_decode_from_blurred_qr(qr, sample_record):
    """Moderately blurred QR should still decode (H error correction)."""
    from PIL import ImageFilter
    
    qr_bytes = qr.encode_record(sample_record)
    
    # CRITICAL: Convert to RGB first (QR PNGs are often mode 'P' or '1')
    img = Image.open(BytesIO(qr_bytes)).convert("RGB")
    
    # Upscale first (avoid destroying modules)
    if min(img.size) < 500:
        scale = 500 / min(img.size)
        img = img.resize(
            (int(img.width * scale), int(img.height * scale)),
            Image.LANCZOS,
        )
    
    # Light blur only (heavy blur destroys dense QRs)
    blurred = img.filter(ImageFilter.GaussianBlur(radius=0.5))
    
    buf = BytesIO()
    blurred.save(buf, format="PNG")
    
    decoded = qr.decode_record(buf.getvalue())
    assert decoded is not None, "Blurred QR failed to decode"


def test_decode_from_resized_qr(qr, sample_record):
    """Downscaled QR (400x400) should still decode with H correction."""
    qr_bytes = qr.encode_record(sample_record)
    
    # CRITICAL: Convert to RGB
    img = Image.open(BytesIO(qr_bytes)).convert("RGB")
    
    # Realistic degraded-scan size
    small = img.resize((400, 400), Image.LANCZOS)
    
    buf = BytesIO()
    small.save(buf, format="PNG")
    
    decoded = qr.decode_record(buf.getvalue())
    assert decoded is not None, "Resized QR failed to decode"


# ============================================================
# BATCH OPERATIONS
# ============================================================

def test_batch_generation(qr, crypto):
    """Batch generation should return one QR per record."""
    records = []
    for i in range(3):
        doc_hash = crypto.compute_document_hash(f"doc-{i}".encode())
        records.append(crypto.build_integrity_record(
            document_id=f"LK-BATCH-{i:03d}",
            document_hash=doc_hash,
            signature_hash="a" * 64,
            ai_confidence=0.9 + i * 0.01,
        ))
    
    qr_bytes_list = qr.generate_qr_batch(records)
    
    assert len(qr_bytes_list) == 3
    for qr_bytes, original in zip(qr_bytes_list, records):
        decoded = qr.decode_record(qr_bytes)
        assert decoded["doc_id"] == original["doc_id"]