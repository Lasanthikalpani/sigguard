"""
RQ3 Layer 5: Document Amendment Service.

Provides legitimate amendment of government documents while
preserving cryptographic integrity.

Key idea (SigVerify RQ3 theory):
  When a citizen needs to change information in their document
  (e.g., surname after marriage), a NEW document is issued with:
    - a NEW QR code
    - a NEW content_hash (reflects the new content)
    - a NEW metadata_hash (reflects the new timestamp)
    - a NEW signature
  and the ledger records:
    - original_doc_id  (lineage)
    - amendment_reason (audit trail)
    - evidence         (e.g., marriage cert ID)

Without Layer 5:
  - Legitimate amendments fail content-hash verification
  - Fraudsters can fake documents using old QR + new content

With Layer 5:
  - Legitimate amendments verify as FULLY_AUTHENTIC (amended)
  - Fake amendments (old QR + new content) still fail as TAMPERED
"""
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

from src.api.services.crypto_service import CryptoService
from src.api.services.qr_service import QRService
from src.api.services.blockchain_service import BlockchainLedger


class AmendmentService:
    """
    Issues and verifies amended documents.

    Terminology:
      original    — the document being amended
      amended     — the new document issued after amendment
      lineage     — original → amendment_1 → amendment_2 → ...
    """

    # Supported amendment types (from Layer 5 design doc)
    SUPPORTED_REASONS = {
        "surname_change": "Surname change (e.g., after marriage)",
        "address_change": "Address change (new residence)",
        "date_correction": "Date correction (wrong date fixed)",
        "info_addition": "Information addition (e.g., blood group)",
        "error_correction": "Error correction (typo, wrong info)",
    }

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
    # ISSUE AMENDMENT
    # ============================================================

    def issue_amendment(
        self,
        original_doc_id: str,
        new_content_bytes: bytes,
        new_signature_bytes: bytes,
        amendment_reason: str,
        evidence: Optional[Dict[str, Any]] = None,
        issuer: str = "Registrar General's Office",
    ) -> Dict[str, Any]:
        """
        Issue an amended document.

        Steps (per Layer 5 design doc):
          1. Verify the original exists in the ledger
          2. Compute new content_hash + signature_hash
          3. Build new integrity record
          4. Encode new QR
          5. Record amendment in blockchain (with lineage)
          6. Return everything needed to issue the new document

        Args:
            original_doc_id: ID of the document being amended
            new_content_bytes: PNG/JPEG of the new document content
            new_signature_bytes: PNG of the new signature region
            amendment_reason: One of SUPPORTED_REASONS keys
            evidence: Optional dict (e.g., {"marriage_cert": "MC-2026-001"})
            issuer: Issuing authority

        Returns:
            dict with keys:
                amended_doc_id, new_qr_base64, new_record,
                original_doc_id, amendment_reason, issued_at,
                blockchain (block_hash, index)
        """
        # ---- Validation ----
        if amendment_reason not in self.SUPPORTED_REASONS:
            raise ValueError(
                f"Unsupported amendment reason: {amendment_reason}. "
                f"Supported: {list(self.SUPPORTED_REASONS.keys())}"
            )

        if self.ledger is None:
            raise RuntimeError("BlockchainLedger required for amendments")

        original = self.ledger.get_document(original_doc_id)
        if original is None:
            raise ValueError(f"Original document not found: {original_doc_id}")

        # ---- Compute new hashes ----
        new_content_hash = self.crypto.compute_content_hash_with_mask(
            new_content_bytes
        )
        new_sig_hash = self.crypto.compute_signature_hash(new_signature_bytes)

        # ---- Generate new doc_id ----
        existing = self.ledger.get_amendments(original_doc_id)
        amended_doc_id = f"{original_doc_id}-AMD-{len(existing) + 1:03d}"

        # ---- Build new integrity record ----
        new_record = self.crypto.build_integrity_record(
            document_id=amended_doc_id,
            document_hash=new_content_hash,
            signature_hash=new_sig_hash,
            ai_confidence=0.95,
            metadata={
                "issuer": issuer,
                "is_amendment": True,
                "original_doc_id": original_doc_id,
                "amendment_reason": amendment_reason,
            },
        )

        # ---- Encode new QR ----
        qr_bytes = self.qr.encode_record(new_record)

        # ---- Record in blockchain ----
        block = self.ledger.add_amendment(
            original_doc_id=original_doc_id,
            new_content_hash=new_content_hash,
            new_sig_hash=new_sig_hash,
            amendment_reason=amendment_reason,
            new_doc_id=amended_doc_id,
            issuer=issuer,
            evidence=evidence,
        )

        # ---- Embed QR into new document ----
        stamped_bytes = self.qr.embed_in_document(
            new_content_bytes,
            qr_bytes,
            position="bottom-right",
        )

        import base64
        return {
            "amended_doc_id": amended_doc_id,
            "original_doc_id": original_doc_id,
            "amendment_reason": amendment_reason,
            "amendment_reason_display": self.SUPPORTED_REASONS[amendment_reason],
            "new_qr_base64": base64.b64encode(qr_bytes).decode("ascii"),
            "stamped_document_base64": base64.b64encode(stamped_bytes).decode("ascii"),
            "new_record": new_record,
            "blockchain": {
                "block_hash": block["block_hash"],
                "block_index": block["index"],
            },
            "issued_at": datetime.utcnow().isoformat() + "Z",
        }

    # ============================================================
    # VERIFY AMENDMENT
    # ============================================================

    def verify_amendment(
        self,
        document_bytes: bytes,
    ) -> Dict[str, Any]:
        """
        Verify an (possibly amended) document.

        Returns a status:
          FULLY_AUTHENTIC              — original or amended, all checks pass
          TAMPERED                     — content hash mismatch / HMAC invalid
          AMENDED_AUTHENTIC            — amendment recognized, lineage verified
          QR_MISSING                   — no QR found

        If the document is an amendment, the lineage is included.
        """
        # ---- Decode QR ----
        qr_data = self.qr.decode_from_document(document_bytes)
        if qr_data is None or "_error" in qr_data:
            return {
                "status": "QR_MISSING",
                "details": {"error": "QR not found or unreadable"},
            }

        # ---- Compute current content hash ----
        current_hash = self.crypto.compute_content_hash_with_mask(document_bytes)

        # ---- Verify integrity record ----
        verification = self.crypto.verify_integrity_record(
            qr_data.copy(),
            current_hash,
            skip_document_match=False,
        )

        if not (verification["hmac_valid"] and verification["document_match"]):
            return {
                "status": "TAMPERED",
                "details": verification.get("details", {}),
                "qr_data": qr_data,
            }

        # ---- Look up in ledger ----
        doc_id = qr_data.get("doc_id", "")
        block = self.ledger.get_document(doc_id) if self.ledger else None

        result = {
            "status": "FULLY_AUTHENTIC",
            "document_id": doc_id,
            "details": verification.get("details", {}),
            "qr_data": qr_data,
            "blockchain": None,
            "lineage": None,
        }

        if block is not None:
            meta = block.get("metadata", {})
            is_amendment = meta.get("is_amendment", False)

            result["blockchain"] = {
                "block_index": block["index"],
                "block_hash": block["block_hash"],
                "is_amendment": is_amendment,
                "original_doc_id": meta.get("original_doc_id"),
                "amendment_reason": meta.get("amendment_reason"),
            }

            if is_amendment:
                result["status"] = "AMENDED_AUTHENTIC"
                result["lineage"] = self.ledger.get_amendment_chain(doc_id)

        return result

    # ============================================================
    # LINEAGE QUERY
    # ============================================================

    def get_lineage(self, doc_id: str) -> Dict[str, Any]:
        """Return the full lineage of a document."""
        if self.ledger is None:
            raise RuntimeError("BlockchainLedger required")
        chain = self.ledger.get_amendment_chain(doc_id)
        return {
            "doc_id": doc_id,
            "lineage_length": len(chain),
            "lineage": chain,
        }