"""Unit tests for RQ3 BlockchainLedger."""
import sys
from pathlib import Path
import tempfile
import json

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.blockchain_service import BlockchainLedger


@pytest.fixture
def ledger():
    """Create a fresh ledger for each test (isolated)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test_ledger.json"
        yield BlockchainLedger(ledger_path=str(path))


# ============================================================
# GENESIS / INITIALIZATION
# ============================================================

def test_genesis_block_created(ledger):
    """Ledger should start with a genesis block."""
    assert len(ledger.chain) == 1
    assert ledger.chain[0]["doc_id"] == "GENESIS"
    assert ledger.chain[0]["index"] == 0


def test_genesis_hash_is_set(ledger):
    """Genesis block should have a valid block_hash."""
    assert len(ledger.chain[0]["block_hash"]) == 64


# ============================================================
# ADD DOCUMENT
# ============================================================

def test_add_document(ledger):
    """Adding a document should append a new block."""
    block = ledger.add_document(
        doc_id="LK-1980-BIRTH-001234",
        content_hash="a" * 64,
        sig_hash="b" * 64,
        issuer="GovLK",
        issued_at="1980-05-15T00:00:00Z",
    )

    assert block["index"] == 1
    assert block["doc_id"] == "LK-1980-BIRTH-001234"
    assert block["content_hash"] == "a" * 64
    assert len(block["block_hash"]) == 64


def test_add_multiple_documents(ledger):
    """Adding multiple documents should chain them."""
    for i in range(5):
        ledger.add_document(
            doc_id=f"LK-DOC-{i:03d}",
            content_hash=str(i) * 64,
            sig_hash=str(i) * 64,
        )

    assert len(ledger.chain) == 6   # genesis + 5
    # Check chain linking
    for i in range(1, len(ledger.chain)):
        assert ledger.chain[i]["prev_hash"] == ledger.chain[i - 1]["block_hash"]


def test_block_hash_is_deterministic(ledger):
    """Same block content should produce same hash."""
    block1 = ledger.add_document(
        doc_id="LK-DET-001",
        content_hash="x" * 64,
        sig_hash="y" * 64,
        issued_at="2026-01-01T00:00:00Z",
    )
    # Compute hash again
    computed = ledger._compute_block_hash(block1)
    assert computed == block1["block_hash"]


# ============================================================
# CERTIFIED COPY (Supervisor's key insight!)
# ============================================================

def test_add_certified_copy(ledger):
    """Certified copy should have SAME content_hash as original."""
    original = ledger.add_document(
        doc_id="LK-1980-CERT-001",
        content_hash="original_hash" + "0" * 51,
        sig_hash="sig_hash" + "0" * 56,
        issued_at="1980-01-01T00:00:00Z",
    )

    copy = ledger.add_certified_copy("LK-1980-CERT-001")

    # Same content hash
    assert copy["content_hash"] == original["content_hash"]
    # Different timestamp
    assert copy["issued_at"] != original["issued_at"]
    # Marked as certified copy
    assert copy["metadata"]["is_certified_copy"] is True
    assert copy["metadata"]["original_doc_id"] == "LK-1980-CERT-001"


def test_certified_copy_missing_original(ledger):
    """Certified copy of missing document should raise ValueError."""
    with pytest.raises(ValueError, match="Original document not found"):
        ledger.add_certified_copy("LK-MISSING-999")


def test_certified_copy_chain_continuity(ledger):
    """Certified copy should continue the chain."""
    original = ledger.add_document(
        doc_id="LK-CHAIN-001",
        content_hash="a" * 64,
        sig_hash="b" * 64,
    )
    copy = ledger.add_certified_copy("LK-CHAIN-001")

    assert copy["prev_hash"] == original["block_hash"]
    assert copy["index"] == original["index"] + 1


# ============================================================
# LOOKUP
# ============================================================

def test_get_document_by_id(ledger):
    """Lookup should find documents by doc_id."""
    ledger.add_document(
        doc_id="LK-LOOKUP-001",
        content_hash="a" * 64,
        sig_hash="b" * 64,
    )

    found = ledger.get_document("LK-LOOKUP-001")
    assert found is not None
    assert found["doc_id"] == "LK-LOOKUP-001"


def test_get_document_not_found(ledger):
    """Lookup of missing doc should return None."""
    found = ledger.get_document("LK-NOT-EXIST")
    assert found is None


# ============================================================
# FIND BY CONTENT HASH
# ============================================================

def test_find_by_content_hash(ledger):
    """Should find all blocks with same content hash."""
    hash_val = "same_hash" + "0" * 55
    ledger.add_document(
        doc_id="LK-SAME-001",
        content_hash=hash_val,
        sig_hash="a" * 64,
    )
    ledger.add_certified_copy("LK-SAME-001")

    matches = ledger.find_by_content_hash(hash_val)
    assert len(matches) == 2
    assert matches[0]["doc_id"] == "LK-SAME-001"
    assert matches[1]["metadata"]["is_certified_copy"] is True


def test_find_by_content_hash_no_match(ledger):
    """Search with unknown hash should return empty list."""
    matches = ledger.find_by_content_hash("x" * 64)
    assert matches == []


# ============================================================
# VERIFY CHAIN
# ============================================================

def test_verify_chain_valid(ledger):
    """A valid chain should verify."""
    for i in range(3):
        ledger.add_document(
            doc_id=f"LK-VERIFY-{i:03d}",
            content_hash=str(i) * 64,
            sig_hash=str(i) * 64,
        )

    result = ledger.verify_chain()
    assert result["valid"] is True
    assert result["length"] == 4   # genesis + 3
    assert result["errors"] == []


def test_verify_chain_detects_tampering(ledger):
    """Tampered block should be detected."""
    ledger.add_document(
        doc_id="LK-TAMPER-001",
        content_hash="a" * 64,
        sig_hash="b" * 64,
    )

    # Tamper with the block hash
    ledger.chain[1]["block_hash"] = "0" * 64

    result = ledger.verify_chain()
    assert result["valid"] is False
    assert len(result["errors"]) > 0


# ============================================================
# STATISTICS
# ============================================================

def test_get_stats(ledger):
    """Stats should reflect chain state."""
    for i in range(3):
        ledger.add_document(
            doc_id=f"LK-STATS-{i:03d}",
            content_hash=str(i) * 64,
            sig_hash=str(i) * 64,
        )

    stats = ledger.get_stats()
    assert stats["total_blocks"] == 4
    assert stats["latest_index"] == 3


def test_persistence(tmp_path):
    """Ledger should persist across instantiations."""
    path = tmp_path / "persist_test.json"

    ledger1 = BlockchainLedger(ledger_path=str(path))
    ledger1.add_document(
        doc_id="LK-PERSIST-001",
        content_hash="a" * 64,
        sig_hash="b" * 64,
    )

    # New instance with same path
    ledger2 = BlockchainLedger(ledger_path=str(path))
    assert len(ledger2.chain) == 2
    assert ledger2.get_document("LK-PERSIST-001") is not None


# ============================================================
# SUPERVISOR'S USE CASE: 1980 BIRTH CERTIFICATES
# ============================================================

def test_legacy_birth_certificate_scenario(ledger):
    """
    Simulate the supervisor's use case: 1980 birth certificates.

    Scenario:
    1. 1980: Birth certificate issued (original)
    2. 2024: Certified copy issued (same content, new timestamp)
    3. Both verify correctly
    """
    # 1980: Original issued
    original_hash = "birth_cert_content_1980" + "0" * 38
    original = ledger.add_document(
        doc_id="LK-1980-BIRTH-000001",
        content_hash=original_hash,
        sig_hash="sig_a" + "0" * 59,
        issued_at="1980-05-15T00:00:00Z",
    )

    # 2024: Certified copy issued
    copy = ledger.add_certified_copy("LK-1980-BIRTH-000001")

    # Assertions
    assert original["issued_at"] == "1980-05-15T00:00:00Z"
    assert copy["issued_at"] != original["issued_at"]
    assert copy["content_hash"] == original["content_hash"]

    # Both findable by content hash
    matches = ledger.find_by_content_hash(original_hash)
    assert len(matches) == 2

    # Chain is valid
    assert ledger.verify_chain()["valid"] is True