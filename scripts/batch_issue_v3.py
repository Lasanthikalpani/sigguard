"""
Batch issue DIFFERENT documents with QR — for correct batch testing.

Uses 5 DIFFERENT documents (not copies) so each has a unique QR.
"""
import base64
import shutil
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"
OUTPUT_DIR = Path("test_data/batch_v3")


def main():
    print("=" * 70)
    print("  Batch Issue v3 — 5 DIFFERENT documents")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check API
    try:
        health = requests.get(f"{API}/api/v1/hybrid/health", timeout=3).json()
        print(f"\n[OK] API healthy: {health['status']}")
    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)

    # 5 DIFFERENT documents, matched with 5 DIFFERENT signatures
    pairs = [
        ("doc_01_land_deed.png", "sig_01_sinhala.png"),
        ("doc_02_id_card.png", "sig_02_tamil.png"),
        ("doc_03_birth_cert.png", "sig_03_english.png"),
        ("doc_04_degree.png", "sig_04_mixed_1.png"),
        ("doc_05_vehicle_reg.png", "sig_05_mixed_2.png"),
    ]

    print(f"\n[INFO] Issuing {len(pairs)} DIFFERENT documents...\n")

    issued = []
    for i, (doc_name, sig_name) in enumerate(pairs, start=1):
        doc_path = Path("test_data/documents") / doc_name
        sig_path = Path("test_data/signatures") / sig_name

        if not doc_path.exists() or not sig_path.exists():
            print(f"   [MISS] {doc_name} or {sig_name}")
            continue

        doc_bytes = doc_path.read_bytes()
        sig_bytes = sig_path.read_bytes()

        try:
            r = requests.post(
                f"{API}/api/v1/hybrid/issue-and-embed",
                files={
                    "document": (doc_name, doc_bytes, "image/png"),
                    "signature": (sig_name, sig_bytes, "image/png"),
                },
                data={"issuer": "Government of Sri Lanka", "ai_confidence": "0.95"},
                timeout=60,
            )

            if r.status_code != 200:
                print(f"   [FAIL] {doc_name}: HTTP {r.status_code}")
                continue

            result = r.json()
            stamped = base64.b64decode(result["stamped_document_base64"])

            # Save stamped document
            doc_out = OUTPUT_DIR / f"{i:02d}_authentic.png"
            doc_out.write_bytes(stamped)

            # Copy signature
            sig_out = OUTPUT_DIR / f"{i:02d}_sig.png"
            shutil.copy(sig_path, sig_out)

            issued.append({
                "n": i,
                "doc": doc_name,
                "doc_id": result["document_id"],
                "doc_out": doc_out.name,
                "sig_out": sig_out.name,
            })

            print(f"   [OK] {doc_name}")
            print(f"        doc_id: {result['document_id']}")
            print(f"        saved:  {doc_out.name} + {sig_out.name}")
            print()

        except Exception as e:
            print(f"   [FAIL] {doc_name}: {e}")

    # Now create 2 TAMPERED versions
    print()
    print("=" * 70)
    print("  Creating 2 TAMPERED documents...")
    print("=" * 70)
    print()

    from PIL import Image, ImageDraw

    tamper_sources = [
        (OUTPUT_DIR / "01_authentic.png", OUTPUT_DIR / "04_tampered.png", "TAMPERED NAME 1"),
        (OUTPUT_DIR / "02_authentic.png", OUTPUT_DIR / "05_tampered.png", "TAMPERED NAME 2"),
    ]

    for src, dst, text in tamper_sources:
        if not src.exists():
            print(f"   [MISS] {src}")
            continue
        img = Image.open(src)
        draw = ImageDraw.Draw(img)
        draw.rectangle([50, 200, 400, 240], fill="white")
        draw.text((60, 210), text, fill="red")
        img.save(dst)
        print(f"   [OK] {src.name} -> {dst.name}")

    # Summary
    print()
    print("=" * 70)
    print(f"  COMPLETE — {len(issued)} authentic + 2 tampered")
    print("=" * 70)
    print()
    print(f"Output: {OUTPUT_DIR.absolute()}")
    print()
    print("Document IDs (should be DIFFERENT):")
    for x in issued:
        print(f"   {x['n']}. {x['doc_out']}: {x['doc_id']}")
    print()
    print("Next: Upload ALL 10 files to Batch Verify page")
    print("Expected: Authentic 3, Tampered 2 (out of 5 files uploaded)")
    print()


if __name__ == "__main__":
    main()