import sys, os
sys.path.append("src")

from sigguard.crypto import generate_key_pair

KEYS_DIR = "data/rq3_dataset/rsa_keys"
os.makedirs(KEYS_DIR, exist_ok=True)

PRIVATE = os.path.join(KEYS_DIR, "gov_private_key.pem")
PUBLIC  = os.path.join(KEYS_DIR, "gov_public_key.pem")

generate_key_pair(PRIVATE, PUBLIC)
print(f"[OK] Private key -> {PRIVATE}")
print(f"[OK] Public  key -> {PUBLIC}")