"""
RQ3 Layer 4 — RSA Key Generation

Generates RSA-2048 key pair for digital signatures:
- private.pem — Secret (issuer only)
- public.pem — Shared (for verification)

Theory (Layer 4):
- Private key signs documents
- Public key verifies signatures
"""
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend


KEYS_DIR = Path("keys")


def generate_keys():
    print("=" * 70)
    print("  RQ3 LAYER 4 — RSA Key Generation")
    print("=" * 70)

    KEYS_DIR.mkdir(parents=True, exist_ok=True)

    private_path = KEYS_DIR / "private.pem"
    public_path = KEYS_DIR / "public.pem"

    # Skip if exists
    if private_path.exists() and public_path.exists():
        print("\n[INFO] Keys already exist. Delete them to regenerate.")
        print(f"  Private: {private_path}")
        print(f"  Public:  {public_path}")
        return

    # Generate RSA-2048 key pair
    print("\n[1/3] Generating RSA-2048 key pair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()

    # Save private key
    print("[2/3] Saving private key (SECRET)...")
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_path.write_bytes(private_bytes)
    print(f"  [OK] {private_path} ({len(private_bytes)} bytes)")

    # Save public key
    print("[3/3] Saving public key (SHARED)...")
    public_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_path.write_bytes(public_bytes)
    print(f"  [OK] {public_path} ({len(public_bytes)} bytes)")

    print()
    print("=" * 70)
    print("  [DONE] RSA KEY PAIR GENERATED")
    print("=" * 70)
    print()
    print("IMPORTANT:")
    print(f"  * {private_path} — KEEP SECRET (issuer only)")
    print(f"  * {public_path}  — Share with everyone (verifiers)")
    print()


if __name__ == "__main__":
    generate_keys()