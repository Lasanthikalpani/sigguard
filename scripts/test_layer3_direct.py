"""Direct test for Layer 3 API endpoint."""
import sys
from pathlib import Path

import requests

API = "http://localhost:8000"


def main():
    print("=" * 60)
    print("  Layer 3 API Test")
    print("=" * 60)

    # Check API
    try:
        health = requests.get(f"{API}/api/v1/hybrid/health", timeout=3).json()
        print(f"\n[OK] API: {health['status']}")
    except Exception as e:
        print(f"[ERROR] API not running: {e}")
        return

    # Load document
    doc_path = Path("test_data/documents/test_tsfree_qr_verify.png")
    if not doc_path.exists():
        print(f"\n[ERROR] Not found: {doc_path}")
        print("Run: python scripts/test_timestamp_free_qr.py")
        return

    with open(doc_path, "rb") as f:
        doc_bytes = f.read()

    # Call Layer 3
    print("\nCalling /api/v1/hybrid/verify-layer3...")
    r = requests.post(
        f"{API}/api/v1/hybrid/verify-layer3",
        files={"document": (doc_path.name, doc_bytes, "image/png")},
        timeout=60,
    )

    print(f"\nHTTP {r.status_code}")

    if r.status_code != 200:
        print(f"[ERROR] {r.text}")
        return

    result = r.json()

    # Safe access with .get()
    status = result.get("status", "UNKNOWN")
    content_match = result.get("content_hash_match", False)
    metadata_match = result.get("metadata_hash_match", False)
    signature_valid = result.get("signature_valid", False)
    blockchain_found = result.get("blockchain_found", False)

    print("\n" + "=" * 60)
    print(f"  STATUS: {status}")
    print("=" * 60)

    print(f"\nContent Hash Match:   {content_match}")
    print(f"Metadata Hash Match:  {metadata_match}")
    print(f"Signature Valid:      {signature_valid}")
    print(f"Blockchain Found:     {blockchain_found}")

    details = result.get("details", {})
    if details:
        print("\nDetails:")
        for k, v in details.items():
            print(f"  {k}: {v}")

    # Summary
    print()
    print("=" * 60)
    if status == "FULLY_AUTHENTIC":
        print("  ✅ LAYER 3 VERIFICATION: FULLY AUTHENTIC")
    elif status == "TAMPERED":
        print("  🚨 LAYER 3 VERIFICATION: TAMPERED")
    elif status == "METADATA_MODIFIED":
        print("  ⚠️ LAYER 3 VERIFICATION: METADATA MODIFIED")
    elif status == "AUTHENTIC_NOT_IN_BLOCKCHAIN":
        print("  ⚠️ LAYER 3 VERIFICATION: AUTHENTIC (Not in Blockchain)")
    elif status == "QR_MISSING":
        print("  🚨 LAYER 3 VERIFICATION: QR MISSING")
    else:
        print(f"  ❓ LAYER 3 VERIFICATION: {status}")
    print("=" * 60)


if __name__ == "__main__":
    main()