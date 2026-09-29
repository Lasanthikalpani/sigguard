"""Test /issue-and-embed endpoint directly."""
import base64
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"


def main():
    print("=" * 70)
    print("  Test /issue-and-embed Endpoint")
    print("=" * 70)
    
    # Check API
    try:
        health = requests.get(f"{API}/api/v1/hybrid/health", timeout=3).json()
        print(f"\n✅ API healthy: {health['status']}")
        print(f"   Services: {health['services']}")
    except Exception as e:
        print(f"❌ API not running: {e}")
        sys.exit(1)
    
    # Load test data
    doc_path = Path("test_data/documents/doc_01_land_deed.png")
    sig_path = Path("test_data/signatures/sig_01_sinhala.png")
    
    if not doc_path.exists():
        print(f"❌ Document not found: {doc_path}")
        sys.exit(1)
    if not sig_path.exists():
        print(f"❌ Signature not found: {sig_path}")
        sys.exit(1)
    
    print(f"\n📄 Document: {doc_path} ({doc_path.stat().st_size:,} bytes)")
    print(f"✍️  Signature: {sig_path} ({sig_path.stat().st_size:,} bytes)")
    
    # Call /issue-and-embed
    print(f"\n🚀 Calling POST {API}/api/v1/hybrid/issue-and-embed...")
    
    with open(doc_path, "rb") as f:
        doc_bytes = f.read()
    with open(sig_path, "rb") as f:
        sig_bytes = f.read()
    
    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (doc_path.name, doc_bytes, "image/png"),
            "signature": (sig_path.name, sig_bytes, "image/png"),
        },
        data={"issuer": "Test Authority", "ai_confidence": "0.95"},
        timeout=60,
    )
    
    print(f"\n📥 Response: HTTP {r.status_code}")
    
    if r.status_code != 200:
        print(f"❌ Failed: {r.text}")
        sys.exit(1)
    
    result = r.json()
    print(f"\n✅ Success!")
    print(f"   Document ID:  {result['document_id']}")
    print(f"   QR size:      {len(result['qr_base64'])} b64 chars")
    print(f"   Stamped size: {len(result['stamped_document_base64'])} b64 chars")
    
    # Save stamped document
    stamped_bytes = base64.b64decode(result["stamped_document_base64"])
    qr_bytes = base64.b64decode(result["qr_base64"])
    
    output_doc = Path("test_data/documents/test_issue_embed_with_qr.png")
    output_qr = Path("test_data/documents/test_issue_embed_qr.png")
    
    with open(output_doc, "wb") as f:
        f.write(stamped_bytes)
    with open(output_qr, "wb") as f:
        f.write(qr_bytes)
    
    print(f"\n💾 Saved:")
    print(f"   Stamped doc: {output_doc} ({len(stamped_bytes):,} bytes)")
    print(f"   QR code:     {output_qr} ({len(qr_bytes):,} bytes)")
    
    # Verify QR can be decoded
    from src.api.services.qr_service import QRService
    qr = QRService()
    decoded = qr.decode_from_document(stamped_bytes)
    
    print(f"\n🔍 QR Decode test:")
    if decoded:
        print(f"   ✅ Decoded!")
        print(f"   doc_id: {decoded.get('doc_id')}")
        print(f"   Match:  {decoded.get('doc_id') == result['document_id']}")
    else:
        print(f"   ❌ Failed to decode")
    
    print("\n" + "=" * 70)
    print("  ✅ END-TO-END TEST COMPLETE")
    print("=" * 70)
    print()
    print("Next steps:")
    print(f"  1. Open the stamped image: {output_doc}")
    print(f"  2. Verify it shows QR in bottom-right corner")
    print(f"  3. Go to Streamlit → 🔍 Hybrid Verify")
    print(f"  4. Upload stamped doc + signature")
    print()


if __name__ == "__main__":
    main()