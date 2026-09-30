"""
RQ3: RSA Signature Service (Layer 2 — Crypto)

Following the SigVerify theory:
- Private Key: stored at issuing office (signs documents)
- Public Key: distributed freely (verifies signatures)

Without RSA:
- Anyone can create fake documents (SHA-256 is public)
- Issuer identity not cryptographically proven
- Non-repudiation fails
- Not legally admissible

With RSA:
- Only issuer can sign (private key required)
- Issuer identity proven (public key verification)
- Non-repudiation enforced
- Legally admissible as digital evidence
"""
import hashlib
import json
from pathlib import Path
from typing import Optional, Dict, Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature


class RSAService:
    """
    RSA signature service for SigVerify.

    Uses RSA-2048 with PSS padding (modern standard).
    """

    def __init__(
        self,
        private_key_path: str = "data/rsa_keys/gov_private_key.pem",
        public_key_path: str = "data/rsa_keys/gov_public_key.pem",
    ):
        self.private_key_path = Path(private_key_path)
        self.public_key_path = Path(public_key_path)
        self._private_key = None
        self._public_key = None

    # ============================================================
    # KEY LOADING
    # ============================================================

    def _load_private_key(self):
        """Load private key from disk (lazy)."""
        if self._private_key is None:
            if not self.private_key_path.exists():
                raise FileNotFoundError(
                    f"Private key not found: {self.private_key_path}\n"
                    f"Run: python scripts/generate_rsa_keys.py"
                )
            with open(self.private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(),
                    password=None,
                )
        return self._private_key

    def _load_public_key(self):
        """Load public key from disk (lazy)."""
        if self._public_key is None:
            if not self.public_key_path.exists():
                raise FileNotFoundError(
                    f"Public key not found: {self.public_key_path}\n"
                    f"Run: python scripts/generate_rsa_keys.py"
                )
            with open(self.public_key_path, "rb") as f:
                self._public_key = serialization.load_pem_public_key(f.read())
        return self._public_key

    # ============================================================
    # SIGN (Issuer only — private key)
    # ============================================================

    def sign_record(self, record: Dict[str, Any]) -> str:
        """
        Sign an integrity record with the issuer's private key.

        Theory (SigVerify):
            Only the issuing office has the private key.
            Thief cannot sign documents.

        Args:
            record: Integrity record (dict without 'signature' field)

        Returns:
            Base64-encoded RSA signature
        """
        import base64

        # Canonical JSON (deterministic)
        canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))

        private_key = self._load_private_key()

        # Sign with RSA-PSS + SHA-256
        signature = private_key.sign(
            canonical.encode("utf-8"),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH,
            ),
            hashes.SHA256(),
        )

        return base64.b64encode(signature).decode("ascii")

    # ============================================================
    # VERIFY (Anyone — public key)
    # ============================================================

    def verify_record(
        self,
        record: Dict[str, Any],
        signature_b64: str,
    ) -> bool:
        """
        Verify an RSA signature with the issuer's public key.

        Theory (SigVerify):
            Public key distributed freely.
            Anyone can verify, but only issuer can sign.

        Args:
            record: Integrity record (without 'signature' field)
            signature_b64: Base64-encoded RSA signature

        Returns:
            True if signature is valid
        """
        import base64

        try:
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            signature = base64.b64decode(signature_b64)
            public_key = self._load_public_key()

            public_key.verify(
                signature,
                canonical.encode("utf-8"),
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH,
                ),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    # ============================================================
    # KEY INFO (for debugging/audit)
    # ============================================================

    def get_public_key_fingerprint(self) -> str:
        """SHA-256 fingerprint of the public key."""
        public_key = self._load_public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(pem).hexdigest()

    def get_public_key_pem(self) -> str:
        """Return PEM-formatted public key (for distribution)."""
        public_key = self._load_public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return pem.decode("utf-8")


# Singleton
_rsa_service = None


def get_rsa_service() -> RSAService:
    """Get the singleton RSA service."""
    global _rsa_service
    if _rsa_service is None:
        _rsa_service = RSAService()
    return _rsa_service