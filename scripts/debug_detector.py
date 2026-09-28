"""Debug OpenCV and WeChat QR detector availability."""
import cv2
import numpy as np
import qrcode
from io import BytesIO
from PIL import Image


def main():
    print("=" * 60)
    print("QR Detector Debug")
    print("=" * 60)
    
    # 1. OpenCV version
    print(f"\n1. OpenCV version: {cv2.__version__}")
    
    # 2. wechat_qrcode module available?
    has_module = hasattr(cv2, "wechat_qrcode")
    print(f"2. Has wechat_qrcode module: {has_module}")
    
    if has_module:
        try:
            print(f"   Submodule: {cv2.wechat_qrcode}")
            print(f"   Has WeChatQRCode class: {hasattr(cv2.wechat_qrcode, 'WeChatQRCode')}")
        except Exception as e:
            print(f"   Error accessing submodule: {e}")
    
    # 3. Try to create WeChat detector
    print(f"\n3. Attempting to create WeChat detector...")
    try:
        w = cv2.wechat_qrcode_WeChatQRCode()
        print(f"   ✅ Created successfully: {w}")
    except Exception as e:
        print(f"   ❌ Failed: {type(e).__name__}: {e}")
        w = None
    
    # 4. Test with a simple QR
    print(f"\n4. Testing with simple QR...")
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H)
    qr.add_data("hello world")
    qr.make(fit=True)
    img = qr.make_image().convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    
    arr = np.frombuffer(buf.getvalue(), dtype=np.uint8)
    cvimg = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    print(f"   QR image shape: {cvimg.shape}")
    
    # Try WeChat
    if w is not None:
        try:
            results, points = w.detectAndDecode(cvimg)
            print(f"   WeChat detected: {results}")
        except Exception as e:
            print(f"   WeChat detection error: {e}")
    
    # Try standard
    try:
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(cvimg)
        print(f"   Standard detected: {data!r}")
    except Exception as e:
        print(f"   Standard detection error: {e}")
    
    print(f"\n{'='*60}")
    print("Diagnosis complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()