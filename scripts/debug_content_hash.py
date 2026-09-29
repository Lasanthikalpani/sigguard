"""
Debug content hash mismatch between issue and verify.

Usage:
    python scripts/debug_content_hash.py
"""
import base64
import io
import sys
from pathlib import Path

import requests
from PIL import Image
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.crypto_service import CryptoService

API = "http://localhost:8000"


def main():
    print("=" * 70)
    print("  Debug Content Hash")
    print("=" * 70)

    crypto = CryptoService()

    # 1. Load test document
    doc_path = Path("test_data/documents/doc_01_land_deed.png")
    if not doc_path.exists():
        print(f"[ERROR] Not found: {doc_path}")
        return

    doc_bytes = doc_path.read_bytes()
    print(f"\n1. Document: {doc_path.name} ({len(doc_bytes):,} bytes)")

    # 2. Check original document hashes
    print(f"\n2. Original document hashes:")
    h_plain = crypto.compute_document_hash(doc_bytes)
    h_masked = crypto.compute_content_hash_with_mask(doc_bytes)
    print(f"   compute_document_hash:          {h_plain[:32]}...")
    print(f"   compute_content_hash_with_mask: {h_masked[:32]}...")

    # 3. Issue document via API
    print(f"\n3. Issuing via API...")
    sig_path = Path("test_data/signatures/sig_01_sinhala.png")
    sig_bytes = sig_path.read_bytes()

    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (doc_path.name, doc_bytes, "image/png"),
            "signature": (sig_path.name, sig_bytes, "image/png"),
        },
        data={"issuer": "Test", "ai_confidence": "0.95"},
        timeout=60,
    )

    if r.status_code != 200:
        print(f"[ERROR] Issue failed: {r.status_code} — {r.text}")
        return

    result = r.json()
    stamped_bytes = base64.b64decode(result["stamped_document_base64"])

    print(f"   doc_id: {result['document_id']}")
    print(f"   QR's doc_hash: {result['integrity_record']['doc_hash'][:32]}...")

    # 4. Check stamped document hashes
    print(f"\n4. Stamped document hashes:")
    h_stamped_plain = crypto.compute_document_hash(stamped_bytes)
    h_stamped_masked = crypto.compute_content_hash_with_mask(stamped_bytes)
    print(f"   compute_document_hash:          {h_stamped_plain[:32]}...")
    print(f"   compute_content_hash_with_mask: {h_stamped_masked[:32]}...")

    # 5. Key comparison: QR record hash vs stamped masked hash
    expected = result["integrity_record"]["doc_hash"]
    actual = crypto.compute_content_hash_with_mask(stamped_bytes)

    print(f"\n5. CRITICAL COMPARISON:")
    print(f"   QR record doc_hash:        {expected}")
    print(f"   Stamped masked hash:       {actual}")
    print(f"   MATCH: {expected == actual}")

    if expected != actual:
        print(f"\n   [MISMATCH!] Content hash function is not stable!")
        print(f"   This is why Authentic documents show CRYPTO_TAMPER.")

        # Try to figure out why
        print(f"\n   Diagnosis:")
        print(f"   - Original doc masked hash:  {h_masked[:32]}...")
        print(f"   - Stamped doc masked hash:   {h_stamped_masked[:32]}...")
        print(f"   - Original vs Stamped: {h_masked == h_stamped_masked}")

        if h_masked == h_stamped_masked:
            print(f"   → Masking works! Issue-time hash from API is different.")
            print(f"     → Check if API is using the same function!")
        else:
            print(f"   → Masking region is WRONG!")
            print(f"     → The QR embed changes pixels OUTSIDE the mask region.")
            print(f"     → Increase the mask region in compute_content_hash_with_mask")

        # Save images for inspection
        Path("test_data/debug_original.png").write_bytes(doc_bytes)
        Path("test_data/debug_stamped.png").write_bytes(stamped_bytes)
        print(f"\n   Saved debug images:")
        print(f"   - test_data/debug_original.png")
        print(f"   - test_data/debug_stamped.png")
    else:
        print(f"\n   [OK] Hashes match! Issue/verify are consistent.")

    # 6. Show QR region inspection
    print(f"\n6. QR region (bottom-right of stamped):")
    img = Image.open(io.BytesIO(stamped_bytes)).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]
    print(f"   Image size: {w} × {h}")

    # Default mask region
    x1, y1 = int(w * 0.55), int(h * 0.55)
    x2, y2 = w, h
    print(f"   Default mask region: ({x1}, {y1}) to ({x2}, {y2})")

    # Check if QR is within this region
    # QR is bottom-right at (w - qr_size - 20, h - qr_size - 20)
    qr_size = max(400, int(min(w, h) * 0.35))
    qr_x1 = w - qr_size - 20
    qr_y1 = h - qr_size - 20
    print(f"   QR region (est):     ({qr_x1}, {qr_y1}) to ({w}, {h})")
    print(f"   QR size est:         {qr_size} × {qr_size}")
    print(f"   QR within mask?      {qr_x1 >= x1 and qr_y1 >= y1}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()