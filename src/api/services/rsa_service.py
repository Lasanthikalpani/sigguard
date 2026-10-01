"""
RQ3 Layer 4 — RSA Digital Signature Service

Theory (Layer 4):
- Digital Signature = Document's digital royal seal
- Created with PRIVATE KEY (issuer only)
- Verified with PUBLIC KEY (shared with everyone)
- 100% tamper detection via Avalanche Effect
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature


class RSAService:
    """
    RSA Digital Signature Service for LAYER 4.

    Combines content_hash + metadata_hash, signs with private key,
    verifies with public key.
    """

    VERSION = "1.0"

    def __init__(
        self,
        private_key_path: str = "keys/private.pem",
        public_key_path: str = "keys/public.pem",
    ):
        self.private_key_path = Path(private_key_path)
        self.public_key_path = Path(public_key_path)

        self._private_key = None
        self._public_key = None

    # ============================================================
    # KEY LOADING
    # ============================================================

    def _load_private_key(self):
        if self._private_key is None:
            if not self.private_key_path.exists():
                raise FileNotFoundError(
                    f"Private key not found: {self.private_key_path}. "
                    f"Run: python scripts/generate_rsa_keys.py"
                )
            with open(self.private_key_path, "rb") as f:
                self._private_key = serialization.load_pem_private_key(
                    f.read(), password=None
                )
        return self._private_key

    def _load_public_key(self):
        if self._public_key is None:
            if not self.public_key_path.exists():
                raise FileNotFoundError(
                    f"Public key not found: {self.public_key_path}. "
                    f"Run: python scripts/generate_rsa_keys.py"
                )
            with open(self.public_key_path, "rb") as f:
                self._public_key = serialization.load_pem_public_key(f.read())
        return self._public_key

    # ============================================================
    # COMBINED HASH (Theory: Layer 4, Step 2)
    # ============================================================

    @staticmethod
    def compute_combined_hash(
        content_hash: str,
        metadata_hash: str,
    ) -> str:
        """
        Theory:
            combined_hash = SHA256(content_hash + metadata_hash)
        """
        combined = f"{content_hash}{metadata_hash}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    # ============================================================
    # SIGN (Theory: Layer 4, Step 2 - Step 5)
    # ============================================================

    def sign_document(
        self,
        content_hash: str,
        metadata_hash: str,
    ) -> Dict[str, Any]:
        """
        Sign document with private key (RSA-2048 + SHA-256).

        Theory:
            signature = RSA_SIGN(combined_hash, private_key)

        Returns:
            {
                "signature": "hex string",
                "combined_hash": "hex string",
                "algorithm": "RSA-2048-PKCS1-SHA256",
                "version": "1.0"
            }
        """
        private_key = self._load_private_key()

        # Step 1: Combine hashes
        combined_hash = self.compute_combined_hash(content_hash, metadata_hash)

        # Step 2: Sign with private key
        signature = private_key.sign(
            combined_hash.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )

        return {
            "signature": signature.hex(),
            "combined_hash": combined_hash,
            "algorithm": "RSA-2048-PKCS1-SHA256",
            "version": self.VERSION,
        }

    # ============================================================
    # VERIFY (Theory: Layer 4, Step 4)
    # ============================================================

    def verify_document(
        self,
        content_hash: str,
        metadata_hash: str,
        signature_hex: str,
    ) -> Dict[str, Any]:
        """
        Verify signature with public key.

        Theory:
            RSA_VERIFY(signature, combined_hash, public_key)
            -> Valid / Invalid

        Returns:
            {
                "valid": bool,
                "combined_hash": "hex",
                "reason": "string"
            }
        """
        result = {
            "valid": False,
            "combined_hash": None,
            "reason": None,
        }

        try:
            public_key = self._load_public_key()
        except FileNotFoundError as e:
            result["reason"] = f"Public key not found: {e}"
            return result

        # Recalculate combined hash
        combined_hash = self.compute_combined_hash(content_hash, metadata_hash)
        result["combined_hash"] = combined_hash

        # Decode signature
        try:
            signature = bytes.fromhex(signature_hex)
        except Exception as e:
            result["reason"] = f"Invalid signature format: {e}"
            return result

        # Verify
        try:
            public_key.verify(
                signature,
                combined_hash.encode("utf-8"),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            result["valid"] = True
            result["reason"] = "Signature valid"
        except InvalidSignature:
            result["valid"] = False
            result["reason"] = "Signature INVALID — document tampered or wrong key"
        except Exception as e:
            result["valid"] = False
            result["reason"] = f"Verification error: {e}"

        return result

    # ============================================================
    # STATS
    # ============================================================

    def get_key_info(self) -> Dict[str, Any]:
        """Return info about loaded keys."""
        info = {
            "private_key_path": str(self.private_key_path),
            "public_key_path": str(self.public_key_path),
            "private_key_exists": self.private_key_path.exists(),
            "public_key_exists": self.public_key_path.exists(),
        }
        if info["public_key_exists"]:
            try:
                pk = self._load_public_key()
                info["key_size"] = pk.key_size
                info["public_key_numbers"] = str(pk.public_numbers().n)[:16] + "..."
            except Exception as e:
                info["error"] = str(e)
        return info


# Singleton
_rsa = None


def get_rsa() -> RSAService:
    global _rsa
    if _rsa is None:
        _rsa = RSAService()
    return _rsa