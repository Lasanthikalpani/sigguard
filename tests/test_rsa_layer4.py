"""
Tests for LAYER 4: RSA Digital Signature (SigVerify Theory).

Validates:
- Key generation
- Sign + Verify (valid)
- Tamper detection (content change)
- Tamper detection (metadata change)
- Avalanche effect
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.rsa_service import RSAService


@pytest.fixture(scope="module")
def rsa():
    """Load RSA service with generated keys."""
    keys_dir = Path("keys")
    if not (keys_dir / "private.pem").exists():
        pytest.skip("RSA keys not found. Run: python scripts/generate_rsa_keys.py")
    return RSAService()


# ============================================================
# COMBINED HASH
# ============================================================

def test_combined_hash_deterministic(rsa):
    """Same inputs → same combined hash."""
    h1 = rsa.compute_combined_hash("a" * 64, "b" * 64)
    h2 = rsa.compute_combined_hash("a" * 64, "b" * 64)
    assert h1 == h2


def test_combined_hash_content_change(rsa):
    """Content hash change → combined hash change."""
    h1 = rsa.compute_combined_hash("a" * 64, "b" * 64)
    h2 = rsa.compute_combined_hash("x" * 64, "b" * 64)
    assert h1 != h2


def test_combined_hash_metadata_change(rsa):
    """Metadata hash change → combined hash change."""
    h1 = rsa.compute_combined_hash("a" * 64, "b" * 64)
    h2 = rsa.compute_combined_hash("a" * 64, "y" * 64)
    assert h1 != h2


# ============================================================
# SIGN
# ============================================================

def test_sign_produces_signature(rsa):
    """Signing produces a hex signature."""
    result = rsa.sign_document("a" * 64, "b" * 64)
    assert "signature" in result
    assert len(result["signature"]) > 0
    assert result["algorithm"] == "RSA-2048-PKCS1-SHA256"


def test_sign_is_deterministic_hash(rsa):
    """Combined hash is deterministic."""
    r1 = rsa.sign_document("a" * 64, "b" * 64)
    r2 = rsa.sign_document("a" * 64, "b" * 64)
    assert r1["combined_hash"] == r2["combined_hash"]


# ============================================================
# VERIFY
# ============================================================

def test_verify_valid_signature(rsa):
    """Valid signature passes verification."""
    signed = rsa.sign_document("a" * 64, "b" * 64)
    result = rsa.verify_document("a" * 64, "b" * 64, signed["signature"])
    assert result["valid"] is True


def test_verify_content_tampered(rsa):
    """Content change → signature verification fails."""
    signed = rsa.sign_document("a" * 64, "b" * 64)
    # Tamper with content hash
    result = rsa.verify_document("x" * 64, "b" * 64, signed["signature"])
    assert result["valid"] is False
    assert "INVALID" in result["reason"]


def test_verify_metadata_tampered(rsa):
    """Metadata change → signature verification fails."""
    signed = rsa.sign_document("a" * 64, "b" * 64)
    result = rsa.verify_document("a" * 64, "y" * 64, signed["signature"])
    assert result["valid"] is False


def test_verify_signature_tampered(rsa):
    """Tampered signature → verification fails."""
    signed = rsa.sign_document("a" * 64, "b" * 64)
    tampered_sig = "0" * len(signed["signature"])
    result = rsa.verify_document("a" * 64, "b" * 64, tampered_sig)
    assert result["valid"] is False


# ============================================================
# AVALANCHE EFFECT
# ============================================================

def test_avalanche_effect_single_bit_change(rsa):
    """
    Theory: Avalanche Effect.
    Single character change → completely different hash.
    """
    h1 = rsa.compute_combined_hash("a" * 64, "b" * 64)
    h2 = rsa.compute_combined_hash("a" * 63 + "c", "b" * 64)  # Change last char
    assert h1 != h2

    # Count matching characters (should be ~half due to avalanche)
    matches = sum(1 for a, b in zip(h1, h2) if a == b)
    assert matches < 32  # Less than half matching


# ============================================================
# KEY INFO
# ============================================================

def test_key_info(rsa):
    """Key info should return valid metadata."""
    info = rsa.get_key_info()
    assert info["private_key_exists"] is True
    assert info["public_key_exists"] is True
    assert info["key_size"] == 2048