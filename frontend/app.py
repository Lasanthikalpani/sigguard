"""SigGuard Streamlit Frontend."""
import streamlit as st
import requests
import base64

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SigGuard - RQ1 & RQ3",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ SigGuard: Document & Signature Verification")
st.subheader("AI-Powered Signature Forgery Detection (RQ1) + QR/Blockchain Hybrid System (RQ3)")

with st.sidebar:
    st.header("About")
    st.write("MSc Research: Explainable AI for Signature Forgery Detection in Sri Lankan Government Documents")
    st.write("**RQ1 (AI):** Siamese CNN")
    st.write("**RQ3 (Crypto):** QR + Blockchain + Dual-Hash")
    
    # API Health Check
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("API Online")
    except Exception:
        st.error("API Offline")

st.markdown("---")

# ============================================================
# TABS FOR RQ1 AND RQ3
# ============================================================
tab1, tab2, tab3 = st.tabs(["📝 RQ1: Signature Verification (AI)", "📄 RQ3: Issue Document (Crypto)", "📚 RQ3: Blockchain Ledger"])

# ============================================================
# TAB 1: RQ1 - Signature Verification (Your Existing Code)
# ============================================================
with tab1:
    st.header("RQ1: Signature Verification (Siamese CNN)")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Reference Signature")
        reference = st.file_uploader(
            "Upload genuine signature",
            type=["png", "jpg", "jpeg"],
            key="reference",
        )
        if reference:
            st.image(reference, use_container_width=True)

    with col2:
        st.subheader("Test Signature")
        test = st.file_uploader(
            "Upload signature to verify",
            type=["png", "jpg", "jpeg"],
            key="test",
        )
        if test:
            st.image(test, use_container_width=True)

    st.markdown("---")

    if st.button("Verify Signature", type="primary", use_container_width=True):
        if not reference or not test:
            st.warning("Please upload both signatures")
        else:
            with st.spinner("Verifying..."):
                try:
                    files = {
                        "reference": (reference.name, reference.getvalue(), "image/png"),
                        "test": (test.name, test.getvalue(), "image/png"),
                    }
                    response = requests.post(f"{API_URL}/verify", files=files)

                    if response.status_code == 200:
                        result = response.json()

                        st.markdown("---")
                        st.header("Verification Result")

                        verdict = result["verdict"]
                        confidence = result["confidence"]
                        distance = result["distance"]
                        inference_time = result["inference_time_ms"]

                        if verdict == "genuine":
                            st.success(f"### ✅ GENUINE")
                        elif verdict == "uncertain":
                            st.warning(f"### ⚠️ UNCERTAIN - Manual Review Required")
                        else:
                            st.error(f"### ❌ FORGED")

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Confidence", f"{confidence:.2%}")
                        col2.metric("Distance", f"{distance:.4f}")
                        col3.metric("Time", f"{inference_time:.0f} ms")

                        st.progress(confidence)
                    else:
                        st.error(f"API Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 2: RQ3 - Issue Document (New Code)
# ============================================================
with tab2:
    st.header("RQ3: Issue New Document (QR + Blockchain)")
    st.info("Upload a document and signature to issue a new ORIGINAL document with a QR code.")

    col1, col2 = st.columns(2)
    with col1:
        doc_file = st.file_uploader("Upload Document Image", type=["png", "jpg", "jpeg"], key="issue_doc")
        doc_id = st.text_input("Document ID", "BC-2026-000099", key="issue_id")
    with col2:
        sig_file = st.file_uploader("Upload Signature Image", type=["png", "jpg", "jpeg"], key="issue_sig")
        doc_type = st.selectbox("Document Type", ["BIRTH_CERTIFICATE", "LAND_DEED", "NATIONAL_ID", "EDUCATION_CERT"], key="issue_type")

    if st.button("Issue Document", type="primary", key="btn_issue"):
        if doc_file and sig_file:
            files = {
                "document": (doc_file.name, doc_file.getvalue(), "image/png"),
                "signature": (sig_file.name, sig_file.getvalue(), "image/png")
            }
            data = {
                "document_id": doc_id,
                "document_type": doc_type,
                "issuer": "Registrar General's Office",
                "ai_confidence": 0.95
            }
            
            with st.spinner("Issuing document..."):
                response = requests.post(f"{API_URL}/api/v1/hybrid/issue", files=files, data=data)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("✅ Document Issued Successfully!")
                    
                    # QR රූපය පෙන්වන්න
                    qr_base64 = result.get("qr_base64")
                    if qr_base64:
                        qr_bytes = base64.b64decode(qr_base64)
                        st.image(qr_bytes, caption="Generated QR Code", width=200)
                    
                    st.write("### Integrity Record")
                    st.json(result["integrity_record"])
                else:
                    st.error(f"Error: {response.text}")
        else:
            st.warning("Please upload both document and signature.")


# ============================================================
# TAB 3: RQ3 - Blockchain Ledger Lookup (New Code)
# ============================================================
with tab3:
    st.header("RQ3: Blockchain Ledger Lookup")
    st.info("Search for a document in the group-wise blockchain ledger to see ORIGINAL vs CERTIFIED_COPY.")

    content_hash = st.text_input("Content Hash", "9af59a6be244320d2ff70a4214d4b0b75fa159515b7fb7077e086931b2da63a2", key="ledger_hash")
    doc_type = st.selectbox("Document Type", ["BIRTH_CERTIFICATE", "LAND_DEED", "NATIONAL_ID", "EDUCATION_CERT"], key="ledger_type")

    if st.button("Search Ledger", type="primary", key="btn_ledger"):
        with st.spinner("Searching..."):
            params = {"content_hash": content_hash, "document_type": doc_type}
            response = requests.get(f"{API_URL}/api/v1/hybrid/ledger/find-by-hash", params=params)
            
            if response.status_code == 200:
                result = response.json()
                st.success(f"Found {result['matches']} block(s)")
                
                for block in result["blocks"]:
                    status = block.get('metadata', {}).get('document_status', 'UNKNOWN')
                    icon = "🟢" if status == "ORIGINAL" else "🔵" if status == "CERTIFIED_COPY" else "⚪"
                    
                    with st.expander(f"{icon} Block {block['index']} - {status} | Doc ID: {block['doc_id']}"):
                        st.write(f"**Issued At:** {block['issued_at']}")
                        st.write(f"**Copy Of:** {block['metadata'].get('copy_of', '-')}")
                        st.write(f"**Block Hash:** `{block['block_hash'][:32]}...`")
                        st.write(f"**Content Hash:** `{block['content_hash'][:32]}...`")
            else:
                st.error(f"Error: {response.text}")

st.caption("SigGuard v2 | MSc Research | RQ1 (AI) + RQ3 (Blockchain)")
