"""Unit tests for RQ3 CryptoService."""
import pytest
from src.api.services.crypto_service import CryptoService


@pytest.fixture
def crypto():
    return CryptoService(secret_key="test-secret-key-for-testing")


@pytest.fixture
def sample_data():
    return {
        "document": b"%PDF-1.4 sample land deed content...",
        "signature": b"signature-region-bytes",
    }


def test_document_hash_consistency(crypto, sample_data):
    """Same document must produce same hash."""
    h1 = crypto.compute_document_hash(sample_data["document"])
    h2 = crypto.compute_document_hash(sample_data["document"])
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex length


def test_different_documents_different_hash(crypto):
    """Different documents must produce different hashes."""
    h1 = crypto.compute_document_hash(b"document A")
    h2 = crypto.compute_document_hash(b"document B")
    assert h1 != h2


def test_hmac_generation_and_verification(crypto):
    """HMAC should verify correctly for unmodified payload."""
    payload = {"doc_id": "LK-001", "score": 0.95}
    hmac_sig = crypto.generate_hmac(payload)
    assert crypto.verify_hmac(payload, hmac_sig) is True


def test_hmac_detects_tampering(crypto):
    """HMAC must fail when payload is modified."""
    payload = {"doc_id": "LK-001", "score": 0.95}
    hmac_sig = crypto.generate_hmac(payload)
    
    tampered = {"doc_id": "LK-001", "score": 0.10}
    assert crypto.verify_hmac(tampered, hmac_sig) is False


def test_build_integrity_record(crypto):
    """Complete record building should work."""
    record = crypto.build_integrity_record(
        document_id="LK-1234567890",
        document_hash="a" * 64,
        signature_hash="b" * 64,
        ai_confidence=0.92,
        metadata={"issuer": "GovLK"},
    )
    
    assert record["v"] == "1.0"
    assert record["doc_id"] == "LK-1234567890"
    assert record["ai_conf"] == 0.92
    assert "hmac" in record
    assert "ts" in record


def test_verify_integrity_record_valid(crypto):
    """Valid record should verify successfully."""
    doc_hash = crypto.compute_document_hash(b"original document")
    
    record = crypto.build_integrity_record(
        document_id="LK-TEST-001",
        document_hash=doc_hash,
        signature_hash="c" * 64,
        ai_confidence=0.95,
    )
    
    result = crypto.verify_integrity_record(record, doc_hash)
    
    assert result["hmac_valid"] is True
    assert result["document_match"] is True
    assert result["timestamp_valid"] is True
    assert result["tamper_detected"] is False


def test_verify_integrity_record_tampered_content(crypto):
    """Record must fail if document content changed."""
    original_hash = crypto.compute_document_hash(b"original document")
    tampered_hash = crypto.compute_document_hash(b"tampered document")
    
    record = crypto.build_integrity_record(
        document_id="LK-TEST-002",
        document_hash=original_hash,
        signature_hash="d" * 64,
        ai_confidence=0.95,
    )
    
    result = crypto.verify_integrity_record(record, tampered_hash)
    
    assert result["document_match"] is False
    assert result["tamper_detected"] is True


def test_verify_integrity_record_tampered_qr(crypto):
    """Record must fail if QR content (HMAC) is tampered."""
    doc_hash = crypto.compute_document_hash(b"document")
    record = crypto.build_integrity_record(
        document_id="LK-TEST-003",
        document_hash=doc_hash,
        signature_hash="e" * 64,
        ai_confidence=0.95,
    )
    
    # Tamper with the record (change doc_id but keep old HMAC)
    record["doc_id"] = "LK-HACKED"
    
    result = crypto.verify_integrity_record(record, doc_hash)
    
    assert result["hmac_valid"] is False
    assert result["tamper_detected"] is True


def test_crypto_score_calculation(crypto):
    """Score calculation should weight components correctly."""
    all_valid = {
        "hmac_valid": True,
        "document_match": True,
        "timestamp_valid": True,
    }
    assert crypto.compute_crypto_score(all_valid) == 1.0
    
    hmac_fail = {
        "hmac_valid": False,
        "document_match": True,
        "timestamp_valid": True,
    }
    assert crypto.compute_crypto_score(hmac_fail) == 0.5