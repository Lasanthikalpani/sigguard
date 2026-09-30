"""
Generate RSA key pair for SigVerify (RQ3 Layer 2 — Crypto).

Following the SigVerify theory:
- Private Key: stored at issuing office (secret)
- Public Key: distributed freely (verification)

Uses 2048-bit RSA keys (industry standard).
"""
import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


KEYS_DIR = Path("data/rsa_keys")
PRIVATE_KEY_PATH = KEYS_DIR / "gov_private_key.pem"
PUBLIC_KEY_PATH = KEYS_DIR / "gov_public_key.pem"


def main():
    print("=" * 60)
    print("  RSA Key Generation (SigVerify)")
    print("=" * 60)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    # Check existing
    if PRIVATE_KEY_PATH.exists():
        print(f"\n[WARN] Keys already exist:")
        print(f"  Private: {PRIVATE_KEY_PATH}")
        print(f"  Public:  {PUBLIC_KEY_PATH}")
        overwrite = input("\nOverwrite? (y/N): ").strip().lower()
        if overwrite != "y":
            print("[INFO] Keeping existing keys.")
            return

    # Generate RSA 2048-bit key pair
    print("\n[1/3] Generating RSA-2048 private key...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_pem)
    print(f"  ✅ Saved: {PRIVATE_KEY_PATH}")

    # Extract and serialize public key
    print("\n[2/3] Extracting public key...")
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_pem)
    print(f"  ✅ Saved: {PUBLIC_KEY_PATH}")

    # Fingerprint (SHA-256 of public key)
    import hashlib
    fingerprint = hashlib.sha256(public_pem).hexdigest()

    print("\n[3/3] Key details:")
    print(f"  Algorithm:   RSA-2048")
    print(f"  Exponent:    65537")
    print(f"  Fingerprint: {fingerprint[:32]}...")
    print()

    print("=" * 60)
    print("  KEY GENERATION COMPLETE")
    print("=" * 60)
    print()
    print("⚠️ IMPORTANT:")
    print(f"  • Private key ({PRIVATE_KEY_PATH}):")
    print(f"      → Keep SECRET at issuing office")
    print(f"      → Never share with anyone")
    print(f"      → Never commit to git (.gitignore it!)")
    print()
    print(f"  • Public key ({PUBLIC_KEY_PATH}):")
    print(f"      → Distribute freely for verification")
    print(f"      → Embed in QR codes / distribute via HTTPS")
    print()


if __name__ == "__main__":
    main()