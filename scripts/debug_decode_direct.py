"""Debug: test decode directly using QRService internal methods."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from io import BytesIO

from src.api.services.qr_service import QRService
from src.api.services.crypto_service import CryptoService


def main():
    print("=" * 60)
    print("Direct Decode Debug")
    print("=" * 60)
    
    crypto = CryptoService()
    qr = QRService()
    
    # Build record and QR
    rec = crypto.build_integrity_record(
        document_id="LK-TEST-001",
        document_hash="a" * 64,
        signature_hash="b" * 64,
        ai_confidence=0.94,
    )
    png = qr.encode_record(rec)
    
    # Load as OpenCV image
    arr = np.frombuffer(png, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    
    print(f"\n1. WeChat detector available: {qr._wechat_detector is not None}")
    print(f"2. Standard detector: {qr._standard_detector is not None}")
    
    # Test 1: _try_wechat
    print(f"\n3. Testing qr._try_wechat(img)...")
    try:
        result = qr._try_wechat(img)
        print(f"   Result: {result}")
        if result:
            print(f"   doc_id: {result.get('doc_id')}")
    except Exception as e:
        import traceback
        print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    # Test 2: _try_standard (on original)
    print(f"\n4. Testing qr._try_standard(img)...")
    try:
        data = qr._try_standard(img)
        print(f"   Data (first 80 chars): {data[:80] if data else 'NONE'}")
        if data:
            parsed = qr._parse_qr_data(data)
            print(f"   Parsed: {parsed}")
            if parsed:
                print(f"   doc_id: {parsed.get('doc_id')}")
    except Exception as e:
        import traceback
        print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    # Test 3: _parse_qr_data with known data
    print(f"\n5. Testing _parse_qr_data with WeChat result...")
    wechat = cv2.wechat_qrcode_WeChatQRCode()
    results, _ = wechat.detectAndDecode(img)
    if results and results[0]:
        raw = results[0]
        print(f"   Raw data type: {type(raw)}")
        print(f"   Raw data length: {len(raw)}")
        print(f"   Raw first 80: {raw[:80]}")
        try:
            parsed = qr._parse_qr_data(raw)
            print(f"   Parsed: {parsed}")
        except Exception as e:
            import traceback
            print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
            traceback.print_exc()
    
    # Test 4: Full decode_record
    print(f"\n6. Testing qr.decode_record(png)...")
    try:
        result = qr.decode_record(png)
        print(f"   Result: {result}")
    except Exception as e:
        import traceback
        print(f"   ❌ EXCEPTION: {type(e).__name__}: {e}")
        traceback.print_exc()
    
    print(f"\n{'='*60}")
    print("Debug complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()