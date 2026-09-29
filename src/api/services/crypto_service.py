"""
RQ3: Cryptographic Service
SHA-256 hashing + HMAC signing for document integrity verification.

Purpose: Provides tamper-evident authentication for Sri Lankan government documents.
Target: >=95% tamper detection reliability.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional


class CryptoService:
    """
    Hybrid cryptographic service for document integrity.
    
    Combines:
    - SHA-256 hashing (content integrity)
    - HMAC-SHA256 signing (tamper evidence)
    - Timestamp validation (freshness)
    """
    
    def __init__(self, secret_key: Optional[str] = None):
        """Initialize with secret key for HMAC signing."""
        self.secret_key = (
            secret_key or os.getenv("SECRET_KEY", "dev-secret-change-in-production")
        ).encode("utf-8")
        self.hash_algorithm = "sha256"
        self.version = "1.0"
    
    # ============================================================
    # HASHING
    # ============================================================
    
    def compute_document_hash(self, document_bytes: bytes) -> str:
        """SHA-256 hash of full document content."""
        return hashlib.sha256(document_bytes).hexdigest()

    def compute_content_hash_with_mask(
        self,
        document_bytes: bytes,
        mask_margin: int = 50,
        mask_value: int = 255,
    ) -> str:
        """
        Compute SHA-256 hash of document content with QR region masked.

        The QR region is determined using the SAME logic as
        QRService.embed_in_document():
        - QR size: max(400, min(w, h) * 0.35)
        - QR position: (w - qr_size - 20, h - qr_size - 20)
        - Mask: QR region + mask_margin pixels around it

        This enables content tamper detection in RQ3 (any tampering
        outside the QR region will change the hash).

        Args:
            document_bytes: Document image bytes (PNG/JPEG)
            mask_margin: Extra pixels to mask around QR region
            mask_value: Pixel value to use for masking (255 = white)

        Returns:
            SHA-256 hex digest of the masked document
        """
        import io
        from PIL import Image
        import numpy as np

        # Load image
        img = Image.open(io.BytesIO(document_bytes)).convert("RGB")
        arr = np.array(img)
        h, w = arr.shape[:2]

        # Determine QR region (same as QRService.embed_in_document)
        qr_size = max(400, int(min(w, h) * 0.35))
        qr_x1 = w - qr_size - 20
        qr_y1 = h - qr_size - 20

        # Mask region: QR region + margin, clamped to image bounds
        x1 = max(0, qr_x1 - mask_margin)
        y1 = max(0, qr_y1 - mask_margin)
        x2 = w
        y2 = h

        # Mask the QR region with uniform color
        arr[y1:y2, x1:x2] = mask_value

        # Hash the masked array bytes
        masked_bytes = arr.tobytes()
        return hashlib.sha256(masked_bytes).hexdigest()
    
    
    def compute_signature_hash(self, signature_bytes: bytes) -> str:
        """SHA-256 hash of extracted signature region."""
        return hashlib.sha256(signature_bytes).hexdigest()
    
    def compute_file_hash(self, file_path: str) -> str:
        """SHA-256 hash of a file (streaming for large files)."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    # ============================================================
    # HMAC SIGNING
    # ============================================================
    
    def generate_hmac(self, payload: Dict[str, Any]) -> str:
        """HMAC-SHA256 signature over canonical JSON payload."""
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hmac.new(
            self.secret_key,
            canonical.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    
    def verify_hmac(self, payload: Dict[str, Any], provided_hmac: str) -> bool:
        """Constant-time HMAC verification (prevents timing attacks)."""
        try:
            expected = self.generate_hmac(payload)
            return hmac.compare_digest(expected, provided_hmac)
        except Exception:
            return False
    
    # ============================================================
    # INTEGRITY RECORD (for QR embedding)
    # ============================================================
    
    def build_integrity_record(
        self,
        document_id: str,
        document_hash: str,
        signature_hash: str,
        ai_confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Build complete integrity record for QR embedding.
        This record gets encoded into the QR code and printed on the document.
        """
        record = {
            "v": self.version,
            "doc_id": document_id,
            "doc_hash": document_hash,
            "sig_hash": signature_hash,
            "ai_conf": round(float(ai_confidence), 4),
            "ts": datetime.utcnow().isoformat() + "Z",
            "issuer": "SigGuard-LK",
            "meta": metadata or {},
        }
        
        # Sign the record
        record["hmac"] = self.generate_hmac(record)
        
        return record
    
    def verify_integrity_record(
        self,
        record: Dict[str, Any],
        current_document_hash: str,
        max_age_days: int = 3650,
        skip_document_match: bool = False,
    ) -> Dict[str, Any]:
        """
        Verify a scanned QR integrity record against current document.
        
        Args:
            record: Integrity record decoded from QR
            current_document_hash: SHA-256 of currently scanned document
            max_age_days: Maximum allowed document age
            skip_document_match: If True, skip the document hash comparison.
                Set this to True when the QR code has been embedded INTO
                the document, because embedding changes the document bytes
                (and therefore the document's SHA-256 hash).
        
        Performs 3 checks:
        1. HMAC validity (detects QR tampering) — ALWAYS checked
        2. Document hash match (detects content tampering) — OPTIONAL
        3. Timestamp freshness — ALWAYS checked
        """
        result = {
            "hmac_valid": False,
            "document_match": False,
            "timestamp_valid": True,
            "tamper_detected": True,
            "details": {},
            "errors": [],
        }
        
        # Guard: check required fields
        required_fields = ["v", "doc_id", "doc_hash", "sig_hash", "hmac"]
        missing = [f for f in required_fields if f not in record]
        if missing:
            result["errors"].append(f"Missing fields: {missing}")
            return result
        
        # ---- Check 1: HMAC verification ----
        record_copy = record.copy()
        provided_hmac = record_copy.pop("hmac", "")
        result["hmac_valid"] = self.verify_hmac(record_copy, provided_hmac)
        result["details"]["hmac"] = "valid" if result["hmac_valid"] else "invalid"
        
        # ---- Check 2: Document hash match (optional) ----
        if skip_document_match:
            result["document_match"] = True
            result["details"]["document_hash"] = "SKIPPED (QR embedded in document)"
        else:
            stored_hash = record.get("doc_hash", "")
            result["document_match"] = hmac.compare_digest(
                stored_hash, current_document_hash
            )
            result["details"]["document_hash"] = (
                "match" if result["document_match"] else "MISMATCH"
            )
            if not result["document_match"]:
                result["details"]["expected_hash"] = stored_hash[:16] + "..."
                result["details"]["actual_hash"] = current_document_hash[:16] + "..."
        
        # ---- Check 3: Timestamp freshness ----
        try:
            ts_str = record.get("ts", "").rstrip("Z")
            ts = datetime.fromisoformat(ts_str)
            age_days = (datetime.utcnow() - ts).days
            result["timestamp_valid"] = 0 <= age_days <= max_age_days
            result["details"]["age_days"] = age_days
            result["details"]["max_age_days"] = max_age_days
        except Exception as e:
            result["timestamp_valid"] = False
            result["errors"].append(f"Timestamp parse error: {e}")
        
        # ---- Final tamper decision ----
        result["tamper_detected"] = not (
            result["hmac_valid"]
            and result["document_match"]
            and result["timestamp_valid"]
        )
        
        return result
    # ============================================================
    # COMPOSITE SCORE (for fusion engine)
    # ============================================================
    
    def compute_crypto_score(self, verification: Dict[str, Any]) -> float:
        """
        Convert crypto verification result to 0-1 score for fusion.
        
        Weighted by component importance:
        - HMAC valid:       0.5 (detects QR tampering)
        - Document match:   0.4 (detects content tampering)
        - Timestamp valid:  0.1 (informational)
        """
        score = 0.0
        if verification.get("hmac_valid"):
            score += 0.5
        if verification.get("document_match"):
            score += 0.4
        if verification.get("timestamp_valid"):
            score += 0.1
        return round(score, 4)