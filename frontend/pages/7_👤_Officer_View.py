"""
RQ3 Page 7 — Officer-Friendly Verification View

Designed for government officers who do NOT have technical knowledge.
Uses SIMPLE LANGUAGE — no technical jargon.

Technical details are hidden under "Advanced Details" (for auditors only).

Simple Language Mapping:
- Merkle Tree → Document Batch Verification
- Merkle Root → Master Signature
- Hash → Digital Fingerprint
- Nonce → Verification Code
- Block → Document Bundle
- Proof-of-Work → Security Verification
- Blockchain → Secure Document Ledger
- Tamper Detection → Forgery Detection
"""
import base64
from io import BytesIO

import requests
import streamlit as st
from PIL import Image

API_URL = "http://localhost:8000"
HYBRID_API = f"{API_URL}/api/v1/hybrid"

st.set_page_config(
    page_title="Document Verification — Sri Lanka Government",
    page_icon="📄",
    layout="wide",
)

# ============================================================
# SIMPLE HEADER (Officer-Friendly)
# ============================================================
st.title("📄 Document Verification")
st.markdown("""
### රජයේ ලේඛන සත්‍යාපනය

Upload a document to check if it is **genuine** or **fake**.

**Simple process — no technical knowledge needed.**
""")

st.divider()

# ============================================================
# API HEALTH (Simple message)
# ============================================================
try:
    health = requests.get(f"{HYBRID_API}/health", timeout=3).json()
    if health.get("status") != "healthy":
        st.warning("⚠️ System is starting up. Please wait a moment.")
except Exception:
    st.error("❌ System is not available. Contact IT support.")
    st.stop()

# ============================================================
# UPLOAD SECTION (Simple)
# ============================================================
st.subheader("📤 Step 1: Upload Document")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**📄 Document with QR Code**")
    st.caption("The complete document you want to verify")
    doc_file = st.file_uploader(
        "Choose document image",
        type=["png", "jpg", "jpeg"],
        key="officer_doc",
    )
    if doc_file:
        st.image(doc_file, caption="✅ Document uploaded", use_container_width=True)

with col2:
    st.markdown("**✍️ Signature Area**")
    st.caption("The signature portion from the same document")
    sig_file = st.file_uploader(
        "Choose signature image",
        type=["png", "jpg", "jpeg"],
        key="officer_sig",
    )
    if sig_file:
        st.image(sig_file, caption="✅ Signature uploaded", use_container_width=True)

# ============================================================
# OPTIONAL REFERENCE
# ============================================================
st.subheader("📤 Step 2: Reference Signature (Optional)")
st.caption("For better accuracy — upload the original signature if you have it")

ref_file = st.file_uploader(
    "Choose reference signature (optional)",
    type=["png", "jpg", "jpeg"],
    key="officer_ref",
)

# ============================================================
# VERIFY BUTTON
# ============================================================
st.divider()

ready = doc_file is not None and sig_file is not None

if not ready:
    st.info("ℹ️ Please upload the document and signature to start.")

if st.button("🔍 Check Document", type="primary", use_container_width=True, disabled=not ready):
    with st.spinner("Checking document... Please wait."):
        files = {
            "document": (doc_file.name, doc_file.getvalue(), doc_file.type or "image/png"),
            "signature": (sig_file.name, sig_file.getvalue(), sig_file.type or "image/png"),
        }
        if ref_file:
            files["reference"] = (ref_file.name, ref_file.getvalue(), ref_file.type or "image/png")

        try:
            r = requests.post(f"{HYBRID_API}/verify", files=files, timeout=60)
            if r.status_code == 200:
                st.session_state["officer_result"] = r.json()
            else:
                st.error("❌ Could not check document. Please try again.")
        except Exception as e:
            st.error(f"❌ Connection problem: {e}")

# ============================================================
# RESULT DISPLAY (Officer-Friendly)
# ============================================================
if "officer_result" in st.session_state:
    result = st.session_state["officer_result"]

    st.divider()
    st.subheader("📋 Result")

    decision = result.get("decision_path", "UNKNOWN")
    is_authentic = result.get("is_authentic", False)
    tamper = result.get("tamper_detected", False)

    # ----------- Simple Verdict (Large, Clear) -----------
    if is_authentic:
        st.success("""
        # ✅ DOCUMENT IS GENUINE
        
        **This document is REAL and has not been changed.**
        
        ✔ You can safely process this document.
        """)
    elif tamper:
        st.error("""
        # 🚨 DOCUMENT IS FAKE
        
        **This document has been CHANGED or FORGED.**
        
        ❌ DO NOT process this document.
        ⚠️ Report to your supervisor immediately.
        """)
    else:
        st.warning("""
        # ⚠️ CANNOT VERIFY
        
        **This document cannot be checked automatically.**
        
        👤 Please give this to a senior officer for manual review.
        """)

    # ----------- Simple Document Information -----------
    st.markdown("### 📄 Document Details")

    col1, col2, col3 = st.columns(3)

    with col1:
        doc_id = result.get("document_id") or "Not available"
        st.markdown(f"**Document ID**\n\n`{doc_id}`")

    with col2:
        verified = result.get("verified_at", "")[:19]
        st.markdown(f"**Checked on**\n\n{verified}")

    with col3:
        if is_authentic:
            st.markdown("**Status**\n\n✅ **VERIFIED**")
        elif tamper:
            st.markdown("**Status**\n\n❌ **NOT VERIFIED**")
        else:
            st.markdown("**Status**\n\n⚠️ **PENDING**")

    # ----------- What This Means (Plain Language) -----------
    st.markdown("### 📖 What This Means")

    if is_authentic:
        st.markdown("""
        ✅ **You can use this document.**
        
        - The QR code is correct
        - The content has not been changed
        - The signature matches official records
        - No forgery detected
        """)
    elif tamper:
        st.markdown("""
        🚨 **This document is not safe.**
        
        - The QR code may be damaged or fake
        - The content may have been changed
        - The signature may be forged
        
        **What to do:** Report to your supervisor.
        """)
    else:
        st.markdown("""
        ⚠️ **Needs manual review.**
        
        - The system cannot confirm if this is real
        - A senior officer should check this document
        """)

    # ============================================================
    # ADVANCED DETAILS (Hidden by default)
    # ============================================================
    st.divider()

    with st.expander("🔧 Advanced Details (For IT Staff / Auditors only)"):
        st.markdown("""
        ⚠️ **This section is for IT staff and auditors only.**
        
        Government officers do NOT need to understand these details.
        """)

        # Technical metrics with simple explanations
        st.markdown("#### 📊 Technical Scores")

        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Overall Confidence",
                f"{result.get('confidence', 0):.1%}",
                help="How confident is the system in this result?"
            )
            st.metric(
                "Signature Match",
                f"{result.get('ai_score', 0):.1%}",
                help="How closely the signature matches the reference"
            )
        with col2:
            st.metric(
                "Document Integrity",
                f"{result.get('crypto_score', 0):.1%}",
                help="Is the document content unchanged?"
            )
            st.metric(
                "Decision Code",
                decision,
                help="Internal decision path"
            )

        # Decision explanation
        decision_meanings = {
            "HYBRID_AUTHENTIC": "✅ AI + Cryptographic verification passed.",
            "AI_SUSPICIOUS": "⚠️ AI detected possible signature forgery.",
            "CRYPTO_TAMPER": "🚨 Content hash mismatch — document modified.",
            "NO_QR": "🚨 No QR code found — document may be forged.",
            "LOW_CONFIDENCE": "⚠️ Confidence too low to decide.",
        }
        st.info(decision_meanings.get(decision, "Unknown decision"))

        # Full JSON
        with st.expander("📋 Full Technical Response"):
            st.json(result)

st.divider()
st.caption("SigGuard LK — Sri Lanka Government Document Verification")