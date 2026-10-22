from sigguard.crypto import rsa_sign, compute_content_hash, compute_metadata_hash

@router.post("/amendment/amend")
async def amend_document(
    original_doc_id: str = Form(...),
    amendment_reason: str = Form(...),
    new_document: UploadFile = File(...),
    new_signature: UploadFile = File(...),
    issuer: str = Form("Registrar General's Office"),
):
    text = (await new_document.read()).decode("utf-8", errors="ignore")
    content_hash  = compute_content_hash(text)
    metadata_hash = compute_metadata_hash(issuer, new_document.filename)
    new_sig = rsa_sign(content_hash, metadata_hash,
                       "data/rq3_dataset/rsa_keys/gov_private_key.pem")   # <-- තැන 1
    return {"amends": original_doc_id, "signature": new_sig,
            "document_type": "AMENDED"}