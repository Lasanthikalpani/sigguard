"""
RQ3: QR Code Service
QR generation, decoding, and embedding for document integrity verification.

Design decisions:
- ERROR_CORRECT_H (30% error correction) for robustness
- OpenCV-contrib WeChat QR detector (primary, high accuracy)
- OpenCV standard QRCodeDetector (fallback)
- Multi-scale preprocessing pipeline
- Target: >=90% QR decode success
"""
import base64
import json
from io import BytesIO
from typing import Dict, Any, Optional

import cv2
import numpy as np
import qrcode
from PIL import Image


class QRService:
    """
    QR generation and decoding service.
    
    Uses ERROR_CORRECT_H (30%) for document degradation resilience.
    Decoding uses OpenCV-contrib WeChat detector (strongest available)
    with fallback to standard OpenCV detector.
    """
    
    VERSION = "1.0"
    
    def __init__(
        self,
        error_correction: int = qrcode.constants.ERROR_CORRECT_H,
        box_size: int = 10,
        border: int = 4,
        qr_scale_in_doc: float = 0.35,
        min_qr_px: int = 400,
    ):
        self.error_correction = error_correction
        self.box_size = box_size
        self.border = border
        self.qr_scale_in_doc = qr_scale_in_doc
        self.min_qr_px = min_qr_px
        
        # Try to load WeChat QR detector (much stronger than standard)
        self._wechat_detector = self._init_wechat_detector()
        self._standard_detector = cv2.QRCodeDetector()
    
    def _init_wechat_detector(self):
        """Initialize WeChat QR detector if available."""
        try:
            return cv2.wechat_qrcode_WeChatQRCode()
        except Exception:
            return None
    
    # ============================================================
    # ENCODING
    # ============================================================
    
    def encode_record(self, record: Dict[str, Any]) -> bytes:
        """Encode integrity record to QR PNG (min 400 px)."""
        payload = json.dumps(record, separators=(",", ":"), sort_keys=True)
        compressed = base64.b64encode(payload.encode("utf-8")).decode("ascii")
        
        qr = qrcode.QRCode(
            version=None,
            error_correction=self.error_correction,
            box_size=self.box_size,
            border=self.border,
        )
        qr.add_data(compressed)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        
        if min(img.size) < self.min_qr_px:
            scale = self.min_qr_px / min(img.size)
            new_size = (int(img.width * scale), int(img.height * scale))
            img = img.resize(new_size, Image.LANCZOS)
        
        buf = BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    
    # ============================================================
    # DECODING
    # ============================================================
    
    def decode_record(self, image_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode QR from image.
        
        Strategy:
        1. WeChat detector (best accuracy)
        2. Standard OpenCV detector (fallback)
        3. Both with grayscale + upscaling + threshold
        """
        # Guard: empty or too-small input
        if not image_bytes or len(image_bytes) < 100:
            return None
        
        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        
        # Strategy 1: WeChat detector
        if self._wechat_detector is not None:
            result = self._try_wechat(img)
            if result is not None and "_error" not in result:
                return result
        
        # Strategy 2: Standard OpenCV with preprocessing variants
        for variant in self._preprocess_variants(img):
            data = self._try_standard(variant)
            if data:
                parsed = self._parse_qr_data(data)
                if parsed is not None and "_error" not in parsed:
                    return parsed
        
        return None
    
    def _try_wechat(self, img) -> Optional[Dict[str, Any]]:
        """Try WeChat QR detector with multiple scales."""
        try:
            # Original
            results, _ = self._wechat_detector.detectAndDecode(img)
            if results and results[0]:
                return self._parse_qr_data(results[0])
            
            # Upscaled
            h, w = img.shape[:2]
            if min(h, w) < 500:
                scale = 500 / min(h, w)
                upscaled = cv2.resize(
                    img, (int(w * scale), int(h * scale)),
                    interpolation=cv2.INTER_CUBIC,
                )
                results, _ = self._wechat_detector.detectAndDecode(upscaled)
                if results and results[0]:
                    return self._parse_qr_data(results[0])
        except Exception:
            pass
        return None
    
    def _try_standard(self, img) -> Optional[str]:
        """Try standard OpenCV QRCodeDetector."""
        try:
            data, _, _ = self._standard_detector.detectAndDecode(img)
            if data:
                return data
        except Exception:
            pass
        return None
    
    def _preprocess_variants(self, img):
        """Generate preprocessing variants of an image."""
        variants = [img]
        
        # Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        variants.append(gray)
        
        # Upscaled versions
        h, w = img.shape[:2]
        for scale in (2.0, 3.0):
            upscaled = cv2.resize(
                img, (int(w * scale), int(h * scale)),
                interpolation=cv2.INTER_CUBIC,
            )
            variants.append(upscaled)
        
        # Otsu threshold
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            variants.append(otsu)
        except Exception:
            pass
        
        # Adaptive threshold
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            thresh = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 51, 10,
            )
            variants.append(thresh)
        except Exception:
            pass
        
        return variants
    
    def _parse_qr_data(self, data: str) -> Optional[Dict[str, Any]]:
        """Parse base64 JSON payload."""
        try:
            payload = base64.b64decode(data).decode("utf-8")
            return json.loads(payload)
        except Exception as e:
            return {"_error": f"Parse error: {e}", "_raw": data[:100]}
    
    # ============================================================
    # EMBEDDING
    # ============================================================
    
    def embed_in_document(
        self,
        document_bytes: bytes,
        qr_bytes: bytes,
        position: str = "bottom-right",
        margin: int = 20,
    ) -> bytes:
        """Embed QR into document at specified position."""
        doc = Image.open(BytesIO(document_bytes)).convert("RGB")
        qr_img = Image.open(BytesIO(qr_bytes)).convert("RGB")
        
        # QR size: max of min_qr_px and scale-based
        qr_size = max(
            self.min_qr_px,
            int(min(doc.width, doc.height) * self.qr_scale_in_doc),
        )
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        
        positions = {
            "bottom-right": (doc.width - qr_size - margin, doc.height - qr_size - margin),
            "bottom-left": (margin, doc.height - qr_size - margin),
            "top-right": (doc.width - qr_size - margin, margin),
            "top-left": (margin, margin),
        }
        pos = positions.get(position, positions["bottom-right"])
        
        doc.paste(qr_img, pos)
        
        buf = BytesIO()
        doc.save(buf, format="PNG")
        return buf.getvalue()
    
    def decode_from_document(self, document_bytes: bytes) -> Optional[Dict[str, Any]]:
        """
        Decode QR from full document.
        
        Strategy:
        1. Try corner crops FIRST (QR is usually in a corner)
        2. Fall back to full document
        3. Try tighter corner crops (for smaller QRs)
        """
        try:
            doc = Image.open(BytesIO(document_bytes)).convert("RGB")
            w, h = doc.size
            
            # Strategy 1: Corner crops (QR is usually in a corner)
            # Use overlapping regions to handle various QR positions
            crops = [
                # Bottom-right (most common)
                (int(w * 0.5), int(h * 0.5), w, h),
                # Bottom-right tighter
                (int(w * 0.65), int(h * 0.65), w, h),
                # Bottom-left
                (0, int(h * 0.5), int(w * 0.5), h),
                # Top-right
                (int(w * 0.5), 0, w, int(h * 0.5)),
                # Top-left
                (0, 0, int(w * 0.5), int(h * 0.5)),
            ]
            
            for box in crops:
                cropped = doc.crop(box)
                buf = BytesIO()
                cropped.save(buf, format="PNG")
                result = self.decode_record(buf.getvalue())
                if result is not None:
                    return result
        except Exception:
            pass
        
        # Strategy 2: Try full document as last resort
        result = self.decode_record(document_bytes)
        if result is not None:
            return result
        
        return None
    
    # ============================================================
    # BATCH / UTILITY
    # ============================================================
    
    def generate_qr_batch(self, records: list) -> list:
        return [self.encode_record(r) for r in records]
    
    def estimate_qr_version(self, record: Dict[str, Any]) -> int:
        payload = json.dumps(record, separators=(",", ":"), sort_keys=True)
        encoded = base64.b64encode(payload.encode()).decode()
        qr = qrcode.QRCode(error_correction=self.error_correction)
        qr.add_data(encoded)
        qr.make(fit=True)
        return qr.version
    
    def get_capacity_bytes(self) -> int:
        return 950
    

# ============================================================
# LAYER 3: QR VERIFICATION — 6 Steps + 4 Scenarios
# ============================================================

class QRVerificationLayer:
    """
    LAYER 3: QR Code Verification (SigVerify Theory)

    Implements 6-step verification process from SigVerify RQ3 paper:
    1. SCAN QR Code
    2. Verify CONTENT HASH
    3. Verify METADATA HASH
    4. Verify SIGNATURE (RSA/HMAC)
    5. Check BLOCKCHAIN
    6. FINAL DECISION

    Returns 4 scenarios:
    - FULLY_AUTHENTIC
    - TAMPERED
    - METADATA_MODIFIED
    - AUTHENTIC_NOT_IN_BLOCKCHAIN
    """

    # Status constants
    FULLY_AUTHENTIC = "FULLY_AUTHENTIC"
    TAMPERED = "TAMPERED"
    METADATA_MODIFIED = "METADATA_MODIFIED"
    AUTHENTIC_NOT_IN_BLOCKCHAIN = "AUTHENTIC_NOT_IN_BLOCKCHAIN"
    QR_MISSING = "QR_MISSING"

    def __init__(self, qr_service=None, crypto_service=None):
        from src.api.services.qr_service import QRService
        from src.api.services.crypto_service import CryptoService
        self.qr = qr_service or QRService()
        self.crypto = crypto_service or CryptoService()

    # ============================================================
    # HELPER: Metadata Hash
    # ============================================================

    @staticmethod
    def compute_metadata_hash(
        timestamp: str,
        issuer: str,
        document_id: str,
    ) -> str:
        """
        Theory (Layer 3, Step 3):
            metadata_hash = SHA256(timestamp + issuer + document_id)
        """
        import hashlib
        canonical = f"{timestamp}|{issuer}|{document_id}"
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ============================================================
    # MAIN: Verify Document
    # ============================================================

    def verify_document(
        self,
        document_bytes: bytes,
        blockchain_ledger=None,
    ) -> dict:
        """
        Full LAYER 3 verification.

        Args:
            document_bytes: Scanned document (PNG/JPEG)
            blockchain_ledger: Optional BlockchainLedger for Step 5

        Returns:
            {
                "status": "FULLY_AUTHENTIC" | "TAMPERED" | ...,
                "content_hash_match": bool,
                "metadata_hash_match": bool,
                "signature_valid": bool,
                "blockchain_found": bool,
                "details": {...},
                "qr_data": {...}
            }
        """
        import hashlib

        # ---------- Step 1: SCAN QR ----------
        qr_data = self.qr.decode_from_document(document_bytes)

        if qr_data is None or "_error" in qr_data:
            return {
                "status": self.QR_MISSING,
                "content_hash_match": False,
                "metadata_hash_match": False,
                "signature_valid": False,
                "blockchain_found": False,
                "details": {"error": "QR code not found or unreadable"},
                "qr_data": None,
            }

        # Extract 6 fields
        qr_content_hash = qr_data.get("doc_hash", "")
        qr_metadata_hash = qr_data.get("metadata_hash", "")
        qr_signature = qr_data.get("hmac", "")
        qr_timestamp = qr_data.get("ts", "")
        qr_issuer = qr_data.get("issuer", "")
        qr_document_id = qr_data.get("doc_id", "")

        # ---------- Step 2: Verify CONTENT HASH ----------
        new_content_hash = self.crypto.compute_content_hash_with_mask(document_bytes)
        content_match = (new_content_hash == qr_content_hash)

        # ---------- Step 3: Verify METADATA HASH ----------
        metadata_match = True
        metadata_note = "not_provided"
        if qr_metadata_hash:
            recomputed = self.compute_metadata_hash(
                qr_timestamp, qr_issuer, qr_document_id
            )
            metadata_match = (recomputed == qr_metadata_hash)
            metadata_note = "verified"
        else:
            metadata_note = "absent_in_qr_v2.0"

        # ---------- Step 4: Verify SIGNATURE ----------
        # HMAC verification (RSA in production)
        record_copy = qr_data.copy()
        provided_hmac = record_copy.pop("hmac", "")
        signature_valid = self.crypto.verify_hmac(record_copy, provided_hmac)

        # ---------- Step 5: Check BLOCKCHAIN ----------
        blockchain_found = False
        blockchain_note = "not_checked"
        if blockchain_ledger is not None:
            block = blockchain_ledger.get_document(qr_document_id)
            if block is not None:
                # Match content hash
                blockchain_found = (block.get("content_hash") == qr_content_hash)
                blockchain_note = "found" if blockchain_found else "hash_mismatch"
            else:
                blockchain_note = "not_found"

        # ---------- Step 6: FINAL DECISION ----------
        status = self._decide_status(
            content_match=content_match,
            metadata_match=metadata_match,
            signature_valid=signature_valid,
            blockchain_found=blockchain_found,
            blockchain_checked=(blockchain_ledger is not None),
        )

        return {
            "status": status,
            "content_hash_match": content_match,
            "metadata_hash_match": metadata_match,
            "signature_valid": signature_valid,
            "blockchain_found": blockchain_found,
            "details": {
                "qr_document_id": qr_document_id,
                "qr_issuer": qr_issuer,
                "qr_timestamp": qr_timestamp or "ABSENT",
                "metadata_note": metadata_note,
                "blockchain_note": blockchain_note,
                "new_content_hash": new_content_hash[:32] + "...",
                "qr_content_hash": qr_content_hash[:32] + "...",
            },
            "qr_data": qr_data,
        }

    # ============================================================
    # DECISION LOGIC (4 Scenarios from Theory)
    # ============================================================

    def _decide_status(
        self,
        content_match: bool,
        metadata_match: bool,
        signature_valid: bool,
        blockchain_found: bool,
        blockchain_checked: bool,
    ) -> str:
        """
        Theory — 4 scenarios:

        Scenario 1: Content ✅ | Metadata ✅ | Signature ✅ | Blockchain ✅
            → FULLY_AUTHENTIC

        Scenario 2: Content ❌ | (Metadata/Blockchain irrelevant)
            → TAMPERED

        Scenario 3: Content ✅ | Metadata ❌
            → METADATA_MODIFIED

        Scenario 4: Content ✅ | Metadata ✅ | Signature ✅ | Blockchain ❌
            → AUTHENTIC_NOT_IN_BLOCKCHAIN
        """
        # Scenario 2: Content tampered (highest priority)
        if not content_match:
            return self.TAMPERED

        # Scenario 3: Metadata modified
        if not metadata_match:
            return self.METADATA_MODIFIED

        # Signature invalid → tampered
        if not signature_valid:
            return self.TAMPERED

        # Scenario 4: Content + metadata + signature OK, but not in blockchain
        if blockchain_checked and not blockchain_found:
            return self.AUTHENTIC_NOT_IN_BLOCKCHAIN

        # Scenario 1: All checks pass
        return self.FULLY_AUTHENTIC

    # ============================================================
    # STATS / DISPLAY
    # ============================================================

    @staticmethod
    def status_display(status: str) -> dict:
        """Return human-readable info for a status."""
        mapping = {
            "FULLY_AUTHENTIC": {
                "emoji": "✅",
                "title": "FULLY AUTHENTIC",
                "message": "All 4 checks passed. Document is genuine.",
                "color": "green",
            },
            "TAMPERED": {
                "emoji": "🚨",
                "title": "TAMPERED",
                "message": "Document content has been modified.",
                "color": "red",
            },
            "METADATA_MODIFIED": {
                "emoji": "⚠️",
                "title": "METADATA MODIFIED",
                "message": "Document content is OK, but metadata changed.",
                "color": "orange",
            },
            "AUTHENTIC_NOT_IN_BLOCKCHAIN": {
                "emoji": "⚠️",
                "title": "AUTHENTIC (Not in Blockchain)",
                "message": "Content is valid, but not yet registered in blockchain.",
                "color": "yellow",
            },
            "QR_MISSING": {
                "emoji": "🚨",
                "title": "QR MISSING",
                "message": "No QR code found. Document may be forged.",
                "color": "red",
            },
        }
        return mapping.get(status, {
            "emoji": "❓",
            "title": status,
            "message": "Unknown status",
            "color": "gray",
        })