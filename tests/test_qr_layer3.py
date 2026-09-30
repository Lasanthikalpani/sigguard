"""
Tests for LAYER 3: QR Code Verification (SigVerify Theory).

Validates:
- 6-step verification process
- 4 verification scenarios
- Metadata hash computation
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.qr_service import QRService, QRVerificationLayer
from src.api.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService(secret_key="layer3-test-secret")


@pytest.fixture
def qr():
    return QRService()


@pytest.fixture
def layer3(qr, crypto):
    return QRVerificationLayer(qr_service=qr, crypto_service=crypto)


# ============================================================
# METADATA HASH
# ============================================================

def test_metadata_hash_deterministic(layer3):
    """Same inputs → same hash."""
    h1 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-001")
    h2 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-001")
    assert h1 == h2
    assert len(h1) == 64


def test_metadata_hash_changes_with_timestamp(layer3):
    """Timestamp change → hash change."""
    h1 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-001")
    h2 = layer3.compute_metadata_hash("2026-09-29T11:00:00Z", "GovLK", "BC-001")
    assert h1 != h2


def test_metadata_hash_changes_with_issuer(layer3):
    """Issuer change → hash change."""
    h1 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-001")
    h2 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "HackerLK", "BC-001")
    assert h1 != h2


def test_metadata_hash_changes_with_document_id(layer3):
    """Document ID change → hash change."""
    h1 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-001")
    h2 = layer3.compute_metadata_hash("2026-09-29T10:00:00Z", "GovLK", "BC-999")
    assert h1 != h2


# ============================================================
# SCENARIO 1: FULLY AUTHENTIC
# ============================================================

def test_scenario_1_fully_authentic(layer3, crypto, qr):
    """Test: Content ✅ | Metadata ✅ | Signature ✅ → FULLY_AUTHENTIC"""

    # Build a valid record with all 6 fields
    from PIL import Image
    from io import BytesIO
    import hashlib

    doc_img = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    doc_img.save(buf, format="PNG")
    doc_bytes = buf.getvalue()

    # Compute content hash
    content_hash = crypto.compute_content_hash_with_mask(doc_bytes)

    # Compute metadata hash
    timestamp = "2026-09-29T10:00:00Z"
    issuer = "Registrar General's Office"
    doc_id = "BC-2026-000001"
    metadata_hash = layer3.compute_metadata_hash(timestamp, issuer, doc_id)

    # Build record (v2.0 with metadata_hash)
    record = {
        "v": "2.0",
        "doc_id": doc_id,
        "doc_hash": content_hash,
        "sig_hash": "sig" + "0" * 61,
        "metadata_hash": metadata_hash,
        "ts": timestamp,
        "issuer": issuer,
    }
    record["hmac"] = crypto.generate_hmac(record)

    # Encode QR
    qr_bytes = qr.encode_record(record)
    stamped = qr.embed_in_document(doc_bytes, qr_bytes)

    # Verify
    result = layer3.verify_document(stamped)

    assert result["content_hash_match"] is True
    assert result["metadata_hash_match"] is True
    assert result["signature_valid"] is True
    assert result["status"] == "FULLY_AUTHENTIC"


# ============================================================
# SCENARIO 2: TAMPERED (Content Changed)
# ============================================================

def test_scenario_2_tampered_content(layer3, crypto, qr):
    """Test: Content ❌ → TAMPERED"""
    from PIL import Image, ImageDraw
    from io import BytesIO

    doc_img = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    doc_img.save(buf, format="PNG")
    doc_bytes = buf.getvalue()

    content_hash = crypto.compute_content_hash_with_mask(doc_bytes)

    record = {
        "v": "2.0",
        "doc_id": "BC-002",
        "doc_hash": content_hash,
        "sig_hash": "a" * 64,
    }
    record["hmac"] = crypto.generate_hmac(record)

    qr_bytes = qr.encode_record(record)
    stamped = qr.embed_in_document(doc_bytes, qr_bytes)

    # Tamper: modify content OUTSIDE QR region
    stamped_img = Image.open(BytesIO(stamped))
    draw = ImageDraw.Draw(stamped_img)
    draw.rectangle([50, 100, 400, 200], fill="red")
    tampered_buf = BytesIO()
    stamped_img.save(tampered_buf, format="PNG")
    tampered = tampered_buf.getvalue()

    result = layer3.verify_document(tampered)

    assert result["content_hash_match"] is False
    assert result["status"] == "TAMPERED"


# ============================================================
# SCENARIO 3: METADATA MODIFIED
# ============================================================

def test_scenario_3_metadata_modified(layer3, crypto, qr):
    """Test: Content ✅ | Metadata ❌ → METADATA_MODIFIED"""
    from PIL import Image
    from io import BytesIO

    doc_img = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    doc_img.save(buf, format="PNG")
    doc_bytes = buf.getvalue()

    content_hash = crypto.compute_content_hash_with_mask(doc_bytes)

    # Original metadata
    timestamp = "2026-09-29T10:00:00Z"
    issuer = "Registrar General's Office"
    doc_id = "BC-003"
    correct_metadata_hash = layer3.compute_metadata_hash(timestamp, issuer, doc_id)

    # But attacker puts a WRONG metadata_hash in QR
    wrong_metadata_hash = "0" * 64

    record = {
        "v": "2.0",
        "doc_id": doc_id,
        "doc_hash": content_hash,
        "sig_hash": "a" * 64,
        "metadata_hash": wrong_metadata_hash,
        "ts": timestamp,
        "issuer": issuer,
    }
    record["hmac"] = crypto.generate_hmac(record)

    qr_bytes = qr.encode_record(record)
    stamped = qr.embed_in_document(doc_bytes, qr_bytes)

    result = layer3.verify_document(stamped)

    assert result["content_hash_match"] is True
    assert result["metadata_hash_match"] is False
    assert result["status"] == "METADATA_MODIFIED"


# ============================================================
# SCENARIO 4: NOT IN BLOCKCHAIN
# ============================================================

def test_scenario_4_not_in_blockchain(layer3, crypto, qr, tmp_path):
    """Test: Content ✅ | Metadata ✅ | Signature ✅ | Blockchain ❌ → AUTHENTIC_NOT_IN_BLOCKCHAIN"""
    from PIL import Image
    from io import BytesIO
    from src.api.services.blockchain_service import BlockchainLedger

    doc_img = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    doc_img.save(buf, format="PNG")
    doc_bytes = buf.getvalue()

    content_hash = crypto.compute_content_hash_with_mask(doc_bytes)
    timestamp = "2026-09-29T10:00:00Z"
    issuer = "GovLK"
    doc_id = "BC-004"
    metadata_hash = layer3.compute_metadata_hash(timestamp, issuer, doc_id)

    record = {
        "v": "2.0",
        "doc_id": doc_id,
        "doc_hash": content_hash,
        "sig_hash": "a" * 64,
        "metadata_hash": metadata_hash,
        "ts": timestamp,
        "issuer": issuer,
    }
    record["hmac"] = crypto.generate_hmac(record)

    qr_bytes = qr.encode_record(record)
    stamped = qr.embed_in_document(doc_bytes, qr_bytes)

    # Empty blockchain (no entries)
    ledger = BlockchainLedger(ledger_path=str(tmp_path / "empty_chain.json"))

    result = layer3.verify_document(stamped, blockchain_ledger=ledger)

    assert result["content_hash_match"] is True
    assert result["metadata_hash_match"] is True
    assert result["signature_valid"] is True
    assert result["blockchain_found"] is False
    assert result["status"] == "AUTHENTIC_NOT_IN_BLOCKCHAIN"


# ============================================================
# QR MISSING
# ============================================================

def test_qr_missing(layer3):
    """No QR in document → QR_MISSING"""
    from PIL import Image
    from io import BytesIO

    blank = Image.new("RGB", (1000, 700), color="white")
    buf = BytesIO()
    blank.save(buf, format="PNG")

    result = layer3.verify_document(buf.getvalue())

    assert result["status"] == "QR_MISSING"


# ============================================================
# STATUS DISPLAY
# ============================================================

def test_status_display():
    """Status display returns human-readable info."""
    for status in ["FULLY_AUTHENTIC", "TAMPERED",
                   "METADATA_MODIFIED", "AUTHENTIC_NOT_IN_BLOCKCHAIN",
                   "QR_MISSING"]:
        info = QRVerificationLayer.status_display(status)
        assert "emoji" in info
        assert "title" in info
        assert "message" in info