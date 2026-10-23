"""
copy_service.py — RQ3 Layer 6: Copy vs Original Service.

Distinguishes between 5 document types:
  1. ORIGINAL        — issued by authority, original QR
  2. CERTIFIED_COPY  — registry-issued copy, new QR + new timestamp
  3. PHOTOCOPY       — simple photocopy, original QR, pHash match
  4. AMENDMENT       — legitimate amendment (Layer 5)
  5. TAMPERED        — forged copy, content changed

References:
  - Dual-Hash: exact SHA-256 + perceptual pHash (Hamming ≤ 10 → PHOTOCOPY)
  - Timestamp-QR: metadata_hash = SHA256(issuer + doc_id), NO timestamp
"""
from datetime import datetime
from typing import Dict, Any, Optional

from src.api.services.crypto_service import CryptoService
from src.api.services.qr_service import QRService
from src.api.services.blockchain_service import BlockchainLedger


class CopyService:
    """Layer 6: Distinguish original, certified copy, photocopy, forgery."""

    ORIGINAL = "ORIGINAL"
    CERTIFIED_COPY = "CERTIFIED_COPY"
    PHOTOCOPY = "PHOTOCOPY"
    TAMPERED = "TAMPERED"
    QR_MISSING = "QR_MISSING"
    UNKNOWN = "UNKNOWN"

    def __init__(
        self,
        crypto_service: Optional[CryptoService] = None,
        qr_service: Optional[QRService] = None,
        ledger: Optional[BlockchainLedger] = None,
    ):
        self.crypto = crypto_service or CryptoService()
        self.qr = qr_service or QRService()
        self.ledger = ledger

    # ============================================================
    # ISSUE CERTIFIED COPY
    # ============================================================
    def issue_certified_copy(
        self,
        original_doc_id: str,
        certifier: str = "Registrar General's Office",
        reason: str = "certified_copy_request",
    ) -> Dict[str, Any]:
        if self.ledger is None:
            raise RuntimeError("BlockchainLedger required")
        original = self.ledger.get_document(original_doc_id)
        if original is None:
            raise ValueError(f"Original document not found: {original_doc_id}")

        block = self.ledger.add_certified_copy(
            original_doc_id=original_doc_id, certifier=certifier)
        new_record = self.crypto.build_integrity_record(
            document_id=block["doc_id"],
            document_hash=block["content_hash"],
            signature_hash=block["sig_hash"],
            ai_confidence=0.95,
            metadata={
                "issuer": certifier,
                "is_certified_copy": True,
                "original_doc_id": original_doc_id,
                "certified_reason": reason,
            },
        )
        qr_bytes = self.qr.encode_record(new_record)
        import base64
        return {
            "certified_copy_id": block["doc_id"],
            "original_doc_id": original_doc_id,
            "certifier": certifier,
            "new_qr_base64": base64.b64encode(qr_bytes).decode("ascii"),
            "new_record": new_record,
            "blockchain": {
                "block_hash": block["block_hash"],
                "block_index": block["index"],
            },
            "issued_at": datetime.utcnow().isoformat() + "Z",
        }

    # ============================================================
    # CLASSIFY DOCUMENT (Layer 6 + dual-hash)
    # ============================================================
    def classify_document(
        self,
        document_bytes: bytes,
        original_doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Step 1: Decode QR
        qr_data = self.qr.decode_from_document(document_bytes)
        if qr_data is None or "_error" in qr_data:
            return self._result(self.QR_MISSING,
                                explanation="No QR code found")

        doc_id = qr_data.get("doc_id", "")
        qr_content_hash = qr_data.get("doc_hash", "")

        # Step 2: Verify HMAC
        record_copy = qr_data.copy()
        provided_hmac = record_copy.pop("hmac", "")
        hmac_valid = self.crypto.verify_hmac(record_copy, provided_hmac)
        if not hmac_valid:
            return self._result(self.TAMPERED, doc_id=doc_id,
                                hmac_valid=False,
                                explanation="QR HMAC invalid")

        # Step 3: Verify content hash
        current_hash = self.crypto.compute_content_hash_with_mask(document_bytes)
        content_match = (current_hash == qr_content_hash)

        # Step 3b: pHash fallback (Dual-Hash p.8)
        if not content_match:
            try:
                from PIL import Image
                import io
                doc_image = Image.open(io.BytesIO(document_bytes))
                current_phash = self.crypto.compute_phash(doc_image)
                qr_phash = qr_data.get("phash", "")
                if qr_phash:
                    hamming = self.crypto.hamming_distance(current_phash, qr_phash)
                    if hamming <= 10:
                        return self._result(
                            self.PHOTOCOPY, doc_id=doc_id,
                            hmac_valid=True, content_hash_match=False,
                            original_doc_id=original_doc_id or doc_id,
                            hamming_distance=hamming,
                            explanation=f"Photocopy (pHash Hamming={hamming}≤10)",
                        )
                    else:
                        return self._result(
                            self.TAMPERED, doc_id=doc_id,
                            hmac_valid=True, content_hash_match=False,
                            hamming_distance=hamming,
                            explanation=f"Content modified (Hamming={hamming}>10)",
                        )
            except Exception:
                pass
            return self._result(
                self.TAMPERED, doc_id=doc_id, hmac_valid=True,
                content_hash_match=False,
                explanation="Content hash mismatch",
            )

        # Step 4: Blockchain lookup
        block = self.ledger.get_document(doc_id) if self.ledger else None
        if block is None:
            content_matches = self.ledger.find_by_content_hash(current_hash) if self.ledger else []
            if content_matches:
                registered = content_matches[0]
                return self._result(
                    self.PHOTOCOPY, doc_id=doc_id,
                    hmac_valid=True, content_hash_match=True,
                    in_ledger=False, original_doc_id=registered["doc_id"],
                    explanation=f"Photocopy of {registered['doc_id']}",
                )
            return self._result(
                self.UNKNOWN, doc_id=doc_id, hmac_valid=True,
                content_hash_match=True, in_ledger=False,
                explanation="QR valid but not in ledger",
            )

        # Step 5: Classify by ledger metadata
        meta = block.get("metadata", {})
        # 🆕 AMENDED
        if meta.get("document_status") == "AMENDED":
            return self._result(
                "AMENDED", doc_id=doc_id, hmac_valid=True,
                content_hash_match=True, in_ledger=True,
                original_doc_id=meta.get("amends"),
                explanation=f"Amended document (amends {meta.get('amends')})",
            )
        
        # CERTIFIED_COPY
        if meta.get("is_certified_copy") or meta.get("document_status") == "CERTIFIED_COPY":
            return self._result(
                self.CERTIFIED_COPY, doc_id=doc_id, hmac_valid=True,
                content_hash_match=True, in_ledger=True,
                is_certified_copy=True,
                original_doc_id=meta.get("copy_of"),
                explanation=f"Certified copy of {meta.get('copy_of')}",
            )
        
        # ORIGINAL
        return self._result(
            self.ORIGINAL, doc_id=doc_id, hmac_valid=True,
            content_hash_match=True, in_ledger=True,
            explanation="Registered original document",
        )

        if meta.get("is_certified_copy"):
            return self._result(
                self.CERTIFIED_COPY, doc_id=doc_id, hmac_valid=True,
                content_hash_match=True, in_ledger=True,
                is_certified_copy=True,
                original_doc_id=meta.get("original_doc_id"),
                explanation=f"Certified copy of {meta.get('original_doc_id')}",
            )
        if meta.get("is_amendment"):
            return self._result(
                "AMENDMENT", doc_id=doc_id, hmac_valid=True,
                content_hash_match=True, in_ledger=True,
                original_doc_id=meta.get("original_doc_id"),
                explanation=f"Amendment ({meta.get('amendment_reason')})",
            )
        return self._result(
            self.ORIGINAL, doc_id=doc_id, hmac_valid=True,
            content_hash_match=True, in_ledger=True,
            explanation="Registered original document",
        )

    # ============================================================
    # UTILITY
    # ============================================================
    @staticmethod
    def _result(
        doc_type: str,
        doc_id: Optional[str] = None,
        hmac_valid: bool = False,
        content_hash_match: bool = False,
        in_ledger: bool = False,
        is_certified_copy: bool = False,
        original_doc_id: Optional[str] = None,
        explanation: str = "",
        hamming_distance: Optional[int] = None,
    ) -> Dict[str, Any]:
        return {
            "document_type": doc_type,
            "document_id": doc_id,
            "hmac_valid": hmac_valid,
            "content_hash_match": content_hash_match,
            "in_ledger": in_ledger,
            "is_certified_copy": is_certified_copy,
            "original_doc_id": original_doc_id,
            "hamming_distance": hamming_distance,
            "explanation": explanation,
            "classified_at": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def type_display(doc_type: str) -> Dict[str, str]:
        mapping = {
            "ORIGINAL": {"emoji": "🟢", "label": "ORIGINAL",
                         "description": "Registry-issued original",
                         "color": "green"},
            "CERTIFIED_COPY": {"emoji": "🔵", "label": "CERTIFIED COPY",
                               "description": "Registry-certified copy",
                               "color": "blue"},
            "PHOTOCOPY": {"emoji": "🟡", "label": "PHOTOCOPY",
                          "description": "Simple photocopy",
                          "color": "orange"},
            "AMENDMENT": {"emoji": "🟣", "label": "AMENDMENT",
                          "description": "Legitimate amendment",
                          "color": "violet"},
            "TAMPERED": {"emoji": "🔴", "label": "TAMPERED",
                         "description": "Content or QR modified",
                         "color": "red"},
            "QR_MISSING": {"emoji": "⚫", "label": "QR MISSING",
                           "description": "No QR found",
                           "color": "gray"},
            "UNKNOWN": {"emoji": "⚪", "label": "UNKNOWN",
                        "description": "Could not classify",
                        "color": "gray"},
        }
        return mapping.get(doc_type, {"emoji": "❓", "label": doc_type,
                                       "description": "Unknown",
                                       "color": "gray"})
    