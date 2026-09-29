"""
Embed QR into a document for testing.

Usage:
    python scripts/embed_qr_test.py <document> <signature> [output]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import base64
import requests

from src.api.services.qr_service import QRService


API_URL = "http://localhost:8000"


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/embed_qr_test.py <document> <signature> [output]")
        print()
        print("Example:")
        print("  python scripts/embed_qr_test.py test_data/documents/doc_01_land_deed.png test_data/signatures/sig_01_sinhala.png")
        sys.exit(1)
    
    doc_path = Path(sys.argv[1])
    sig_path = Path(sys.argv[2])
    out_path = Path(sys.argv[3]) if len(sys.argv) > 3 else doc_path.parent / f"{doc_path.stem}_with_qr.png"
    
    if not doc_path.exists():
        print(f"❌ Document not found: {doc_path}")
        sys.exit(1)
    if not sig_path.exists():
        print(f"❌ Signature not found: {sig_path}")
        sys.exit(1)
    
    print("=" * 60)
    print("  QR Embedding Test")
    print("=" * 60)
    print(f"  Document:  {doc_path}")
    print(f"  Signature: {sig_path}")
    print(f"  Output:    {out_path}")
    print()
    
    print("1. Checking API health...")
    try:
        r = requests.get(f"{API_URL}/api/v1/hybrid/health", timeout=3)
        if r.status_code != 200:
            print(f"❌ API unhealthy: {r.status_code}")
            sys.exit(1)
        print(f"   ✅ API healthy")
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print()
        print("Start the API first (in another terminal):")
        print("  conda activate sigguard")
        print("  cd C:\\Users\\lasan\\Desktop\\research\\reserch_july_9\\sigguard")
        print("  python -m uvicorn src.api.main:app --reload")
        sys.exit(1)
    
    print()
    print("2. Issuing document via API...")
    doc_bytes = doc_path.read_bytes()
    sig_bytes = sig_path.read_bytes()
    
    r = requests.post(
        f"{API_URL}/api/v1/hybrid/issue",
        files={
            "document": (doc_path.name, doc_bytes, "image/png"),
            "signature": (sig_path.name, sig_bytes, "image/png"),
        },
        timeout=30,
    )
    if r.status_code != 200:
        print(f"❌ Issue failed: {r.status_code} — {r.text}")
        sys.exit(1)
    issue_data = r.json()
    print(f"   ✅ Document ID: {issue_data['document_id']}")
    print(f"   ✅ Doc hash:   {issue_data['integrity_record']['doc_hash'][:32]}...")
    print(f"   ✅ HMAC:       {issue_data['integrity_record']['hmac'][:32]}...")
    
    print()
    print("3. Embedding QR into document...")
    qr_bytes = base64.b64decode(issue_data["qr_base64"])
    print(f"   QR PNG size: {len(qr_bytes):,} bytes")
    
    qr_service = QRService()
    stamped = qr_service.embed_in_document(doc_bytes, qr_bytes)
    print(f"   Stamped size: {len(stamped):,} bytes")
    
    print()
    print("4. Saving stamped document...")
    out_path.write_bytes(stamped)
    print(f"   ✅ Saved: {out_path}")
    
    print()
    print("=" * 60)
    print("  ✅ QR EMBEDDING COMPLETE!")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"  1. Open Streamlit: http://localhost:8501")
    print(f"  2. Navigate to: 🔍 Hybrid Verify")
    print(f"  3. Upload document:  {out_path}")
    print(f"  4. Upload signature: {sig_path}")
    print(f"  5. Click 'Verify Document'")
    print()


if __name__ == "__main__":
    main()