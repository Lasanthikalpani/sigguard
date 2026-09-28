"""Debug script for QR service — verifies encode/decode roundtrip."""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.qr_service import QRService
from src.api.services.crypto_service import CryptoService


def main():
    print("=" * 60)
    print("QR Service Debug Test")
    print("=" * 60)
    
    crypto = CryptoService()
    qr = QRService()
    
    # Create a test integrity record
    rec = crypto.build_integrity_record(
        document_id="TEST-001",
        document_hash="a" * 64,
        signature_hash="b" * 64,
        ai_confidence=0.95,
    )
    print(f"\n1. Record created:")
    print(f"   doc_id:   {rec['doc_id']}")
    print(f"   ai_conf:  {rec['ai_conf']}")
    print(f"   hmac[:16]: {rec['hmac'][:16]}...")
    
    # Encode to QR
    png = qr.encode_record(rec)
    print(f"\n2. QR encoded:")
    print(f"   PNG size: {len(png)} bytes")
    print(f"   Magic:    {png[:8]}")
    
    # Decode back
    decoded = qr.decode_record(png)
    print(f"\n3. QR decoded:")
    print(f"   Result:   {'SUCCESS' if decoded else 'FAILED'}")
    
    if decoded:
        print(f"   doc_id:   {decoded.get('doc_id')}")
        print(f"   ai_conf:  {decoded.get('ai_conf')}")
        print(f"   hmac[:16]: {str(decoded.get('hmac', ''))[:16]}...")
        
        # Verify match
        match = decoded.get("doc_id") == rec["doc_id"]
        print(f"\n4. Roundtrip match: {'✅ YES' if match else '❌ NO'}")
        
        # Verify crypto
        result = crypto.verify_integrity_record(decoded.copy(), rec["doc_hash"])
        print(f"\n5. Crypto verification:")
        print(f"   HMAC valid:       {result['hmac_valid']}")
        print(f"   Document match:   {result['document_match']}")
        print(f"   Tamper detected:  {result['tamper_detected']}")
        
        if match and not result["tamper_detected"]:
            print(f"\n{'='*60}")
            print("✅ ALL CHECKS PASSED — QR service works correctly!")
            print(f"{'='*60}")
            return 0
        else:
            print(f"\n{'='*60}")
            print("❌ Some checks failed")
            print(f"{'='*60}")
            return 1
    else:
        print(f"\n{'='*60}")
        print("❌ DECODE FAILED — QR could not be decoded")
        print(f"{'='*60}")
        return 1


if __name__ == "__main__":
    sys.exit(main())