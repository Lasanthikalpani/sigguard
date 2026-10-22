from sigguard.crypto import rsa_sign, compute_content_hash, compute_metadata_hash

@router.post("/copy/issue-certified")
async def issue_certified_copy(
    original_doc_id: str = Form(...),
    certifier: str = Form("Registrar General's Office"),
    reason: str = Form("certified_copy_request"),
):
    # Certified copy = same content_hash, NEW signature (new issued_at in blockchain)
    content_hash  = compute_content_hash(original_doc_id)   # lookup from node
    metadata_hash = compute_metadata_hash(certifier, original_doc_id)
    sig = rsa_sign(content_hash, metadata_hash,
                   "data/rq3_dataset/rsa_keys/gov_private_key.pem")      # <-- තැන 1
    return {"copy_of": original_doc_id, "signature": sig,
            "document_type": "CERTIFIED_COPY", "issued_at": "new"}