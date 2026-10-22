# src/sigguard/hybrid/verifier.py

from dataclasses import dataclass
from src.sigguard.hybrid.dual_hash import (
    compute_content_hash, compute_metadata_hash,
    compute_phash, hamming_distance, PHASH_THRESHOLD
)

@dataclass
class VerificationResult:
    result: str              # ORIGINAL | CERTIFIED_COPY | PHOTOCOPY | AMENDED | TAMPERED
    content_hash_match: bool
    metadata_hash_match: bool
    signature_valid: bool
    hamming_distance: int | None
    confidence: float
    reason: str

def verify_dual_hash(
    scanned_content: str,
    scanned_image,
    qr_payload: dict,
    blockchain_block: dict | None,
    phash_threshold: int = PHASH_THRESHOLD,
) -> VerificationResult:
    """
    3.2 Dual-Hash verification logic (Timestamp-QR p.7 + Dual-Hash p.8).
    """
    # Step 1: Exact hash check
    new_content_hash = compute_content_hash(scanned_content)
    new_metadata_hash = compute_metadata_hash(
        qr_payload["issuer"], qr_payload["document_id"])

    content_match = (new_content_hash == qr_payload["content_hash"])
    metadata_match = (new_metadata_hash == qr_payload["metadata_hash"])
    signature_valid = _verify_signature(qr_payload)

    # Step 2: Exact hash + blockchain match
    if content_match and metadata_match and signature_valid and blockchain_block:
        doc_type = blockchain_block.get("document_type", "ORIGINAL")
        if doc_type == "AMENDED" and blockchain_block.get("amends"):
            if _amends_valid(blockchain_block):
                return VerificationResult(
                    result="AMENDED", content_hash_match=True,
                    metadata_hash_match=True, signature_valid=True,
                    hamming_distance=None, confidence=0.98,
                    reason="Amendment verified against original")
            return VerificationResult(
                result="TAMPERED", content_hash_match=True,
                metadata_hash_match=True, signature_valid=True,
                hamming_distance=None, confidence=0.95,
                reason="Amendment chain invalid")
        return VerificationResult(
            result=doc_type, content_hash_match=True,
            metadata_hash_match=True, signature_valid=True,
            hamming_distance=None, confidence=0.97,
            reason="Exact hash + blockchain match")

    # Step 3: Exact hash failed → perceptual hash fallback
    new_phash = compute_phash(scanned_image)
    hamming = hamming_distance(new_phash, qr_payload["phash"])

    if hamming <= phash_threshold:
        return VerificationResult(
            result="PHOTOCOPY", content_hash_match=False,
            metadata_hash_match=metadata_match, signature_valid=signature_valid,
            hamming_distance=hamming, confidence=1 - (hamming / 64),
            reason=f"Exact hash failed but pHash Hamming={hamming}≤{phash_threshold}")

    # Step 4: Both fail → TAMPERED
    return VerificationResult(
        result="TAMPERED", content_hash_match=False,
        metadata_hash_match=metadata_match, signature_valid=signature_valid,
        hamming_distance=hamming, confidence=0.95,
        reason=f"Exact hash + pHash failed (Hamming={hamming})")