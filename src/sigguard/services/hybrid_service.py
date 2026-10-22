# src/sigguard/services/hybrid_service.py

from src.sigguard.hybrid.qr_decoder import decode_qr
from src.sigguard.hybrid.verifier import verify_dual_hash
from src.sigguard.blockchain.router import route_to_node
from src.sigguard.ai.inference import run_dual_stream_cnn, generate_gradcam

def full_hybrid_verify(document_image, signature_image, reference_signature=None):
    """
    /verify endpoint හි steps 1-5 (Swagger description).
    """
    # Step 1: Extract and decode QR
    qr_payload = decode_qr(document_image)

    # Step 2: Verify cryptographic integrity (HMAC + hash + timestamp)
    block = route_to_node(qr_payload["document_type"], qr_payload["document_id"])

    # Step 3: Run AI signature verification (RQ1 Siamese CNN)
    ai_result = run_dual_stream_cnn(signature_image, reference_signature)

    # Step 4: Fuse AI + crypto decisions (dual-hash)
    scanned_content = extract_text(document_image)
    crypto_result = verify_dual_hash(
        scanned_content, document_image, qr_payload, block)

    # Step 5: Return combined verdict with explanations
    gradcam_b64 = generate_gradcam(ai_result)
    return {
        "final_result": _fuse(crypto_result.result, ai_result.label),
        "crypto_confidence": crypto_result.confidence,
        "ai_confidence": ai_result.confidence,
        "hamming_distance": crypto_result.hamming_distance,
        "gradcam_heatmap_base64": gradcam_b64,
        "reason": crypto_result.reason,
    }