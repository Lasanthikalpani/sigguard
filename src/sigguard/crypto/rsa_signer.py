# src/sigguard/crypto/rsa_signer.py

import hashlib
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.exceptions import InvalidSignature

# --- Key management ---------------------------------------------------------

def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def load_public_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def generate_key_pair(private_path: str, public_path: str):
    from cryptography.hazmat.primitives.asymmetric import rsa
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(private_path, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()))
    with open(public_path, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))

# --- Core sign / verify (තැන 1 හි හරය) ------------------------------------

def rsa_sign(content_hash: str, metadata_hash: str, private_key_path: str) -> str:
    private_key = load_private_key(private_key_path)
    message = (content_hash + metadata_hash).encode("utf-8")
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    return signature.hex()

def rsa_verify(signature_hex: str, content_hash: str,
               metadata_hash: str, public_key_path: str) -> bool:
    public_key = load_public_key(public_key_path)
    try:
        public_key.verify(
            bytes.fromhex(signature_hex),
            (content_hash + metadata_hash).encode("utf-8"),
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256())
        return True
    except (InvalidSignature, ValueError):
        return False

# --- Hash helpers (sign එකට පෙර) ------------------------------------------

def compute_content_hash(content_text: str) -> str:
    return hashlib.sha256(content_text.encode("utf-8")).hexdigest()

def compute_metadata_hash(issuer: str, document_id: str) -> str:
    # timestamp NODAI  -> Timestamp-QR solution
    return hashlib.sha256(f"{issuer}|{document_id}".encode("utf-8")).hexdigest()