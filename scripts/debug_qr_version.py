"""Debug: check QR version and test detection with actual integrity record."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import cv2
import numpy as np
from io import BytesIO
from PIL import Image

from src.api.services.qr_service import QRService
from src.api.services.crypto_service import CryptoService


def main():
    print("=" * 60)
    print("QR Version & Detection Debug")
    print("=" * 60)
    
    crypto = CryptoService()
    qr = QRService()
    
    # Build realistic integrity record
    rec = crypto.build_integrity_record(
        document_id="LK-TEST-001",
        document_hash="a" * 64,
        signature_hash="b" * 64,
        ai_confidence=0.94,
    )
    
    # 1. QR version
    version = qr.estimate_qr_version(rec)
    print(f"\n1. QR version needed: {version}")
    print(f"   (version 1-10: easy, 10-20: medium, 20-40: hard)")
    
    # 2. PNG size
    png = qr.encode_record(rec)
    print(f"\n2. QR PNG size: {len(png)} bytes")
    
    # 3. Get actual QR image dimensions
    img = Image.open(BytesIO(png))
    print(f"   Image dimensions: {img.size}")
    print(f"   Image mode: {img.mode}")
    
    # 4. Try decode with WeChat directly
    arr = np.frombuffer(png, dtype=np.uint8)
    cvimg = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    print(f"   CV image shape: {cvimg.shape}")
    
    print(f"\n4. Testing decoders...")
    
    # WeChat on original
    try:
        w = cv2.wechat_qrcode_WeChatQRCode()
        results, points = w.detectAndDecode(cvimg)
        print(f"   WeChat (original): {results if results else 'EMPTY'}")
    except Exception as e:
        print(f"   WeChat error: {e}")
    
    # Standard on original
    try:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cvimg)
        print(f"   Standard (original): {data[:50] if data else 'EMPTY'}")
    except Exception as e:
        print(f"   Standard error: {e}")
    
    # 5. Our QRService decode
    decoded = qr.decode_record(png)
    print(f"\n5. QRService.decode_record: {'SUCCESS' if decoded else 'FAILED'}")
    if decoded:
        print(f"   doc_id: {decoded.get('doc_id')}")
    
    # 6. Save QR for visual inspection
    with open("debug_qr_actual.png", "wb") as f:
        f.write(png)
    print(f"\n6. Saved QR to: debug_qr_actual.png")
    
    print(f"\n{'='*60}")
    print("Analysis complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()