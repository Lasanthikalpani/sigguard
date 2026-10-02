"""
RQ3 Layer 6: Copy vs Original Service.

Distinguishes between 4 document types:
  1. ORIGINAL        — issued by authority, original QR
  2. CERTIFIED_COPY  — registry-issued copy, new QR + new timestamp
  3. PHOTOCOPY       — simple photocopy, original QR, same timestamp
  4. TAMPERED        — forged copy, content changed

Design:
  - Content hash identifies the *information* in the document
  - Metadata hash identifies the *issuance event* (timestamp + issuer + doc_id)
  - Blockchain ledger records all ORIGINAL and CERTIFIED_COPY events
  - A PHOTOCOPY has a valid content hash + metadata hash but no ledger entry
    (it's just a copy of the original QR)
  - A FORGED copy has a mismatched content hash → TAMPERED
"""
from datetime import datetime
from typing import Dict, Any, Optional

from src.api.services.crypto_service import CryptoService
from src.api.services.qr_service import QRService
from src.api.services.blockchain_service import BlockchainLedger


class CopyService:
    """
    Layer 6: Distinguish between original, certified copy, photocopy, and forgery.
    """

    # Document type constants
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
        """
        Issue a registry-certified copy of a document.

        The certified copy has:
          - SAME content hash (information unchanged)
          - NEW metadata hash (new timestamp)
          - NEW QR code
          - Blockchain entry with is_certified_copy: True + original_doc_id

        This is what a government registry does when a citizen requests
        an official copy.
        """
        if self.ledger is None:
            raise RuntimeError("BlockchainLedger required")

        original = self.ledger.get_document(original_doc_id)
        if original is None:
            raise ValueError(f"Original document not found: {original_doc_id}")

        # Record the certified copy in the ledger
        block = self.ledger.add_certified_copy(
            original_doc_id=original_doc_id,
            certifier=certifier,
        )

        # Build a new integrity record for the certified copy
        new_record = self.crypto.build_integrity_record(
            document_id=block["doc_id"],
            document_hash=block["content_hash"],   # SAME as original
            signature_hash=block["sig_hash"],      # SAME
            ai_confidence=0.95,
            metadata={
                "issuer": certifier,
                "is_certified_copy": True,
                "original_doc_id": original_doc_id,
                "certified_reason": reason,
            },
        )

        # Encode new QR
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
    # CLASSIFY DOCUMENT
    # ============================================================

    def classify_document(
        self,
        document_bytes: bytes,
        original_doc_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Classify a document as ORIGINAL, CERTIFIED_COPY, PHOTOCOPY, or TAMPERED.

        Logic:
          1. Decode QR → get doc_id, doc_hash, metadata_hash, hmac
          2. Verify HMAC (QR integrity)
          3. Verify content hash (document body integrity)
          4. Blockchain lookup by doc_id
          5. Determine document type based on ledger metadata

        Args:
            document_bytes: Scanned document (PNG/JPEG)
            original_doc_id: Optional — the claimed original (for photocopy detection)

        Returns:
            {
                "document_type": "ORIGINAL" | "CERTIFIED_COPY" | "PHOTOCOPY" | "TAMPERED" | "QR_MISSING",
                "document_id": str,
                "content_hash_match": bool,
                "hmac_valid": bool,
                "in_ledger": bool,
                "is_certified_copy": bool,
                "original_doc_id": str | None,
                "explanation": str,
            }
        """
        # ---- Step 1: Decode QR ----
        qr_data = self.qr.decode_from_document(document_bytes)
        if qr_data is None or "_error" in qr_data:
            return self._result(
                self.QR_MISSING,
                explanation="No QR code found in document",
            )

        doc_id = qr_data.get("doc_id", "")
        qr_content_hash = qr_data.get("doc_hash", "")

        # ---- Step 2: Verify HMAC ----
        record_copy = qr_data.copy()
        provided_hmac = record_copy.pop("hmac", "")
        hmac_valid = self.crypto.verify_hmac(record_copy, provided_hmac)

        if not hmac_valid:
            return self._result(
                self.TAMPERED,
                doc_id=doc_id,
                hmac_valid=False,
                explanation="QR HMAC invalid — QR itself has been tampered with",
            )

        # ---- Step 3: Verify content hash ----
        current_hash = self.crypto.compute_content_hash_with_mask(document_bytes)
        content_match = (current_hash == qr_content_hash)

        if not content_match:
            return self._result(
                self.TAMPERED,
                doc_id=doc_id,
                hmac_valid=True,
                content_hash_match=False,
                explanation="Content hash mismatch — document content has been modified",
            )

        # ---- Step 4: Blockchain lookup ----
        block = self.ledger.get_document(doc_id) if self.ledger else None

        if block is None:
            # QR is valid, content matches, but doc_id not in ledger.
            # Two possibilities:
            #   (a) PHOTOCOPY of a document that predates the ledger
            #   (b) Unregistered document
            # We can check by content hash against all ledger entries:
            content_matches = self.ledger.find_by_content_hash(current_hash) if self.ledger else []

            if content_matches:
                # A registered document with the same content exists.
                # This is a PHOTOCOPY (original QR copied onto a new sheet).
                registered = content_matches[0]
                return self._result(
                    self.PHOTOCOPY,
                    doc_id=doc_id,
                    hmac_valid=True,
                    content_hash_match=True,
                    in_ledger=False,
                    original_doc_id=registered["doc_id"],
                    explanation=(
                        f"Photocopy of registered document {registered['doc_id']}"
                    ),
                )

            return self._result(
                self.UNKNOWN,
                doc_id=doc_id,
                hmac_valid=True,
                content_hash_match=True,
                in_ledger=False,
                explanation="QR valid but not in ledger, and no matching content found",
            )

        # ---- Step 5: Classify by ledger metadata ----
        meta = block.get("metadata", {})
        is_certified = meta.get("is_certified_copy", False)
        is_amendment = meta.get("is_amendment", False)

        if is_certified:
            return self._result(
                self.CERTIFIED_COPY,
                doc_id=doc_id,
                hmac_valid=True,
                content_hash_match=True,
                in_ledger=True,
                is_certified_copy=True,
                original_doc_id=meta.get("original_doc_id"),
                explanation=(
                    f"Registry-certified copy of {meta.get('original_doc_id')}"
                ),
            )

        if is_amendment:
            # Layer 5 amendment — treat as a distinct document type
            return self._result(
                "AMENDMENT",
                doc_id=doc_id,
                hmac_valid=True,
                content_hash_match=True,
                in_ledger=True,
                original_doc_id=meta.get("original_doc_id"),
                explanation=(
                    f"Amendment of {meta.get('original_doc_id')} "
                    f"({meta.get('amendment_reason')})"
                ),
            )

        # ---- Original ----
        return self._result(
            self.ORIGINAL,
            doc_id=doc_id,
            hmac_valid=True,
            content_hash_match=True,
            in_ledger=True,
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
    ) -> Dict[str, Any]:
        return {
            "document_type": doc_type,
            "document_id": doc_id,
            "hmac_valid": hmac_valid,
            "content_hash_match": content_hash_match,
            "in_ledger": in_ledger,
            "is_certified_copy": is_certified_copy,
            "original_doc_id": original_doc_id,
            "explanation": explanation,
            "classified_at": datetime.utcnow().isoformat() + "Z",
        }

    @staticmethod
    def type_display(doc_type: str) -> Dict[str, str]:
        """Return human-readable info for a document type."""
        mapping = {
            "ORIGINAL": {
                "emoji": "🟢",
                "label": "ORIGINAL",
                "description": "Registry-issued original document",
                "color": "green",
            },
            "CERTIFIED_COPY": {
                "emoji": "🔵",
                "label": "CERTIFIED COPY",
                "description": "Registry-issued certified copy (new QR, new timestamp)",
                "color": "blue",
            },
            "PHOTOCOPY": {
                "emoji": "🟡",
                "label": "PHOTOCOPY",
                "description": "Simple photocopy (original QR, same timestamp)",
                "color": "orange",
            },
            "AMENDMENT": {
                "emoji": "🟣",
                "label": "AMENDMENT",
                "description": "Legitimate amendment (new QR, new content)",
                "color": "violet",
            },
            "TAMPERED": {
                "emoji": "🔴",
                "label": "TAMPERED / FORGED",
                "description": "Content or QR has been modified",
                "color": "red",
            },
            "QR_MISSING": {
                "emoji": "⚫",
                "label": "QR MISSING",
                "description": "No QR code found — not a registered document",
                "color": "gray",
            },
            "UNKNOWN": {
                "emoji": "⚪",
                "label": "UNKNOWN",
                "description": "QR valid but document could not be classified",
                "color": "gray",
            },
        }
        return mapping.get(doc_type, {
            "emoji": "❓",
            "label": doc_type,
            "description": "Unknown document type",
            "color": "gray",
        })