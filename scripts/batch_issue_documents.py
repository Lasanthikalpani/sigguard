"""
Batch issue documents with QR — for RQ3 batch verify testing.

Creates 5 QR-embedded documents from test data.
Saves to: test_data/batch_with_qr/
"""
import base64
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"
OUTPUT_DIR = Path("test_data/batch_with_qr")


def main():
    print("=" * 70)
    print("  Batch Issue Documents with QR")
    print("=" * 70)

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Check API
    try:
        health = requests.get(f"{API}/api/v1/hybrid/health", timeout=3).json()
        print(f"\n[OK] API healthy: {health['status']}")
    except Exception as e:
        print(f"[ERROR] API not running: {e}")
        print("Start API first: python -m uvicorn src.api.main:app --reload")
        sys.exit(1)

    # Document + signature pairs
    pairs = [
        ("doc_01_land_deed.png", "sig_01_sinhala.png"),
        ("doc_02_id_card.png", "sig_02_tamil.png"),
        ("doc_03_birth_cert.png", "sig_03_english.png"),
        ("doc_04_degree.png", "sig_04_mixed_1.png"),
        ("doc_05_vehicle_reg.png", "sig_05_mixed_2.png"),
    ]

    print(f"\n[INFO] Issuing {len(pairs)} documents with QR...\n")

    results = []
    for i, (doc_name, sig_name) in enumerate(pairs, start=1):
        doc_path = Path("test_data/documents") / doc_name
        sig_path = Path("test_data/signatures") / sig_name

        if not doc_path.exists():
            print(f"   [MISS] {doc_path}")
            continue
        if not sig_path.exists():
            print(f"   [MISS] {sig_path}")
            continue

        # Read files
        doc_bytes = doc_path.read_bytes()
        sig_bytes = sig_path.read_bytes()

        # Call issue-and-embed
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
            stamped_bytes = base64.b64decode(result["stamped_document_base64"])

            # Save stamped document
            output_name = f"{i:02d}_{doc_path.stem}_with_qr.png"
            output_path = OUTPUT_DIR / output_name
            output_path.write_bytes(stamped_bytes)

            # Save the signature reference (for later verify)
            sig_output = OUTPUT_DIR / f"{i:02d}_sig_{sig_path.stem}.png"
            sig_output.write_bytes(sig_bytes)

            results.append({
                "doc_id": result["document_id"],
                "doc_file": output_name,
                "sig_file": sig_output.name,
                "stamped_size": len(stamped_bytes),
            })

            print(f"   [OK] {doc_name} -> {output_name}")
            print(f"        doc_id: {result['document_id']}")
            print(f"        size:   {len(stamped_bytes):,} bytes")
            print()

        except Exception as e:
            print(f"   [FAIL] {doc_name}: {e}")

    # Summary
    print()
    print("=" * 70)
    print(f"  COMPLETE — {len(results)} documents issued")
    print("=" * 70)
    print()
    print(f"Output folder: {OUTPUT_DIR.absolute()}")
    print()
    print("Files created:")
    for r in results:
        print(f"   [DOC] {r['doc_file']}")
        print(f"         Pair with: {r['sig_file']}")
        print(f"         Document ID: {r['doc_id']}")
        print()

    print("Next steps:")
    print("  1. Open Streamlit: http://localhost:8501")
    print("  2. Go to: Batch Verify page")
    print(f"  3. Upload documents from: {OUTPUT_DIR}")
    print(f"  4. Upload signatures from: {OUTPUT_DIR}")
    print()


if __name__ == "__main__":
    main()