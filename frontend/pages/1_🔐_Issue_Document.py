"""RQ3 Page 1 — Issue Document with Server-Side QR Embedding."""
import base64

import requests
import streamlit as st

API_URL = "http://localhost:8000"
HYBRID_API = f"{API_URL}/api/v1/hybrid"

st.set_page_config(
    page_title="Issue Document — SigGuard LK",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 Issue Document with QR Integrity Record")
st.markdown("""
**RQ3 — Hybrid Document Verification**

Issue a new document with a cryptographically-signed QR code.
The QR will be **automatically embedded** into the document (server-side).
""")

st.divider()

# ============================================================
# API HEALTH CHECK
# ============================================================
try:
    health = requests.get(f"{HYBRID_API}/health", timeout=3).json()
    if health.get("status") == "healthy":
        st.success("✅ API is healthy")
    else:
        st.warning("⚠️ API not fully healthy")
except Exception:
    st.error(f"❌ Cannot connect to API at {API_URL}")
    st.info("**Start the API first:**\n```\nconda activate sigguard\npython -m uvicorn src.api.main:app --reload\n```")
    st.stop()

st.divider()

# ============================================================
# HELP BOX
# ============================================================
with st.expander("📖 What should I upload? (Click to expand)", expanded=False):
    st.markdown("""
    ### You need TWO images from the SAME document:

    **1. 📄 Full Document (WITHOUT QR)**
    - The **complete** original document image
    - Land deed, ID card, certificate, etc.
    - **Must NOT have a QR code yet** — this page will generate & embed it

    **2. ✍️ Signature Region (CROPPED)**
    - **ONLY the signature area** — cropped from the same document
    - Used by the AI layer to detect forgery
    """)

# ============================================================
# UPLOAD FIELDS
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 1. Full Document (WITHOUT QR)")
    st.caption("Upload the **complete** original document. No QR code yet.")

    doc_file = st.file_uploader(
        "Choose document image",
        type=["png", "jpg", "jpeg"],
        key="issue_doc",
    )
    if doc_file:
        st.image(doc_file, caption="✅ Full document preview", use_container_width=True)
        st.success(f"✅ Document: {doc_file.name} ({len(doc_file.getvalue()):,} bytes)")

with col2:
    st.subheader("✍️ 2. Signature Region (CROPPED)")
    st.caption("Upload **ONLY** the signature portion. Used by AI.")

    sig_file = st.file_uploader(
        "Choose signature image",
        type=["png", "jpg", "jpeg"],
        key="issue_sig",
    )
    if sig_file:
        st.image(sig_file, caption="✅ Signature region preview", use_container_width=True)
        st.success(f"✅ Signature: {sig_file.name} ({len(sig_file.getvalue()):,} bytes)")

# ============================================================
# OPTIONS
# ============================================================
st.divider()
st.subheader("⚙️ Options")

col3, col4, col5 = st.columns(3)
with col3:
    custom_id = st.text_input("Custom Document ID (optional)", placeholder="LK-CUSTOM-001")
with col4:
    issuer = st.text_input("Issuer", value="Government of Sri Lanka")
with col5:
    ai_conf = st.slider("AI Confidence", 0.0, 1.0, 0.95, 0.01)

# ============================================================
# SUBMIT
# ============================================================
st.divider()

ready = doc_file is not None and sig_file is not None

if not ready:
    st.warning("⚠️ Please upload BOTH images above to enable the button.")

if st.button("🚀 Issue Document with QR", type="primary", use_container_width=True, disabled=not ready):
    with st.spinner("Issuing document and embedding QR (server-side)..."):
        files = {
            "document": (doc_file.name, doc_file.getvalue(), doc_file.type or "image/png"),
            "signature": (sig_file.name, sig_file.getvalue(), sig_file.type or "image/png"),
        }
        data = {"issuer": issuer, "ai_confidence": str(ai_conf)}
        if custom_id:
            data["document_id"] = custom_id

        try:
            # Use /issue-and-embed — server-side QR embedding
            r = requests.post(f"{HYBRID_API}/issue-and-embed", files=files, data=data, timeout=60)

            if r.status_code != 200:
                st.error(f"❌ Issue failed: {r.status_code} — {r.text}")
                st.stop()

            result = r.json()

            # Decode both QR and stamped document
            qr_bytes = base64.b64decode(result["qr_base64"])
            stamped_bytes = base64.b64decode(result["stamped_document_base64"])

            # Store in session state
            st.session_state["issued_document"] = result
            st.session_state["stamped_doc_bytes"] = stamped_bytes
            st.session_state["qr_bytes"] = qr_bytes

            st.success("✅ Document issued and QR embedded successfully!")

        except Exception as e:
            st.error(f"❌ Request failed: {e}")

# ============================================================
# DISPLAY RESULT
# ============================================================
if "issued_document" in st.session_state:
    result = st.session_state["issued_document"]
    st.divider()
    st.subheader("📋 Issue Result")

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric("Document ID", result["document_id"])
    with col_b:
        st.metric("Issued At", result["issued_at"][:19])
    with col_c:
        st.metric("QR Size", f"{len(result['qr_base64'])} b64")

    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "🖼️ Stamped Document (with QR)",
        "🔳 QR Code",
        "📋 Integrity Record",
    ])

    with tab1:
        if "stamped_doc_bytes" in st.session_state:
            st.subheader("✅ Document with Embedded QR")
            st.image(
                st.session_state["stamped_doc_bytes"],
                caption=f"Stamped: {result['document_id']}_with_qr.png",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Download Stamped Document (with QR)",
                st.session_state["stamped_doc_bytes"],
                file_name=f"{result['document_id']}_with_qr.png",
                mime="image/png",
                use_container_width=True,
                type="primary",
            )
            st.info("""
            **💡 Next step:** Use this stamped document on the **🔍 Hybrid Verify** page.

            1. Download the stamped document above
            2. Go to **🔍 Hybrid Verify** page
            3. Upload this stamped document + signature + reference
            4. Click Verify
            """)
        else:
            st.warning("⚠️ No stamped document available")

    with tab2:
        st.subheader("QR Code (Standalone)")
        qr_bytes = base64.b64decode(result["qr_base64"])
        st.image(qr_bytes, caption="Integrity QR Code", width=350)
        st.download_button(
            "⬇️ Download QR Code (PNG)",
            qr_bytes,
            file_name=f"{result['document_id']}_qr.png",
            mime="image/png",
            use_container_width=True,
        )

    with tab3:
        st.subheader("Integrity Record (JSON)")
        st.json(result["integrity_record"])
        st.download_button(
            "⬇️ Download Integrity Record (JSON)",
            data=str(result["integrity_record"]).replace("'", '"'),
            file_name=f"{result['document_id']}_record.json",
            mime="application/json",
            use_container_width=True,
        )

st.divider()
st.caption("SigGuard LK — RQ3 Hybrid Verification · MSc Research")
