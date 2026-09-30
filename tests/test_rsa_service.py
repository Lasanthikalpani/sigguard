"""
Tests for RSA Service (SigVerify Layer 2 — Crypto).

Validates:
- Private key signs records
- Public key verifies signatures
- Thief cannot forge (no private key)
- Tampered records fail verification
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.rsa_service import RSAService


@pytest.fixture
def rsa():
    return RSAService()


@pytest.fixture
def sample_record():
    return {
        "v": "2.0",
        "doc_id": "LK-2026-TEST-001",
        "doc_hash": "a" * 64,
        "sig_hash": "b" * 64,
        "ai_conf": 0.95,
        "issuer": "SigGuard-LK",
    }


# ============================================================
# SIGN
# ============================================================

def test_sign_returns_base64(rsa, sample_record):
    """Signing should return base64 string."""
    signature = rsa.sign_record(sample_record)
    assert isinstance(signature, str)
    assert len(signature) > 100  # RSA-2048 → ~344 base64 chars


def test_sign_deterministic_per_call(rsa, sample_record):
    """PSS is randomized → signatures differ, but both verify."""
    s1 = rsa.sign_record(sample_record)
    s2 = rsa.sign_record(sample_record)
    # PSS uses random salt → different signatures
    assert s1 != s2
    # But both should verify
    assert rsa.verify_record(sample_record, s1)
    assert rsa.verify_record(sample_record, s2)


# ============================================================
# VERIFY
# ============================================================

def test_verify_valid_signature(rsa, sample_record):
    """Valid signature should verify."""
    signature = rsa.sign_record(sample_record)
    assert rsa.verify_record(sample_record, signature) is True


def test_verify_tampered_content(rsa, sample_record):
    """Tampered record should fail verification."""
    signature = rsa.sign_record(sample_record)

    tampered = sample_record.copy()
    tampered["doc_hash"] = "HACKED" + "0" * 58

    assert rsa.verify_record(tampered, signature) is False


def test_verify_wrong_signature(rsa, sample_record):
    """Wrong signature should fail."""
    # Sign one record
    signature = rsa.sign_record(sample_record)

    # Verify a DIFFERENT record
    other = sample_record.copy()
    other["doc_id"] = "LK-2026-TEST-999"

    assert rsa.verify_record(other, signature) is False


def test_verify_invalid_base64(rsa, sample_record):
    """Invalid base64 → False (no exception)."""
    assert rsa.verify_record(sample_record, "not-a-valid-signature") is False


def test_verify_empty_signature(rsa, sample_record):
    """Empty signature → False."""
    assert rsa.verify_record(sample_record, "") is False


# ============================================================
# KEY INFO
# ============================================================

def test_public_key_fingerprint(rsa):
    """Fingerprint is 64-char hex string."""
    fp = rsa.get_public_key_fingerprint()
    assert len(fp) == 64
    assert all(c in "0123456789abcdef" for c in fp)


def test_public_key_pem(rsa):
    """Public key PEM starts with header."""
    pem = rsa.get_public_key_pem()
    assert pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert pem.strip().endswith("-----END PUBLIC KEY-----")


# ============================================================
# SUPERVISOR'S THEORY VALIDATION
# ============================================================

def test_thief_cannot_sign_without_private_key(sample_record):
    """
    Theory: Without private key, thief cannot create valid signature.

    We simulate this by signing with one service and verifying with
    a service that has a DIFFERENT key pair.
    """
    import tempfile
    from cryptography.hazmat.primitives.asymmetric import rsa as rsa_prim
    from cryptography.hazmat.primitives import serialization

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Generate two key pairs
        for name in ["gov", "thief"]:
            key = rsa_prim.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            (tmp / f"{name}_private.pem").write_bytes(
                key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
            (tmp / f"{name}_public.pem").write_bytes(
                key.public_key().public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                )
            )

        gov = RSAService(
            private_key_path=str(tmp / "gov_private.pem"),
            public_key_path=str(tmp / "gov_public.pem"),
        )
        thief = RSAService(
            private_key_path=str(tmp / "thief_private.pem"),
            public_key_path=str(tmp / "thief_public.pem"),
        )

        # Thief signs with their key
        thief_signature = thief.sign_record(sample_record)

        # Government verifies with their public key
        # → Must FAIL (signature doesn't match government's key)
        assert gov.verify_record(sample_record, thief_signature) is False