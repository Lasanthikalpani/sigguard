"""RQ3 Page 2 — Hybrid Document Verification (with Reference for AI)."""
import requests
import streamlit as st

API_URL = "http://localhost:8000"
HYBRID_API = f"{API_URL}/api/v1/hybrid"

st.set_page_config(
    page_title="Hybrid Verify — SigGuard LK",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Hybrid Document Verification")
st.markdown("""
**RQ3 — AI + Cryptographic Verification**

| Layer | Purpose | Weight |
|-------|---------|--------|
| 🔐 Cryptographic | QR integrity (HMAC + hash) | 60% |
| 🤖 AI (Siamese CNN) | Signature authenticity | 40% |
""")

st.divider()

# API health check
try:
    health = requests.get(f"{HYBRID_API}/health", timeout=3).json()
    if health.get("status") != "healthy":
        st.warning("⚠️ API not fully healthy")
except Exception:
    st.error(f"❌ Cannot connect to API at {API_URL}")
    st.info("**Start the API:**\n```\npython -m uvicorn src.api.main:app --reload\n```")
    st.stop()

# ============================================================
# UPLOAD FIELDS
# ============================================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📄 Full Document (WITH QR)")
    st.caption("The complete document that has the QR code embedded.")
    doc_file = st.file_uploader(
        "Upload document WITH QR",
        type=["png", "jpg", "jpeg"],
        key="verify_doc",
    )
    if doc_file:
        st.image(doc_file, caption="Document preview", use_container_width=True)

with col2:
    st.subheader("✍️ Signature Region (CROPPED)")
    st.caption("ONLY the signature area — used by AI for comparison.")
    sig_file = st.file_uploader(
        "Upload signature region",
        type=["png", "jpg", "jpeg"],
        key="verify_sig",
    )
    if sig_file:
        st.image(sig_file, caption="Signature preview", use_container_width=True)

# ============================================================
# REFERENCE SIGNATURE (for AI comparison)
# ============================================================
st.divider()
st.subheader("🎯 Reference Signature (for AI)")
st.caption("Upload the ORIGINAL genuine signature used at issue time. The RQ1 Siamese CNN compares it against the test signature.")

with st.expander("📖 Why is the reference signature needed? (Click to expand)", expanded=False):
    st.markdown("""
    **The RQ1 Siamese CNN needs TWO signatures to compare:**

    1. **Reference** — the genuine, original signature
    2. **Test** — the signature you want to verify

    **Without a reference:**
    - The AI layer falls back to a fixed value (0.94)
    - Verification only relies on the cryptographic (QR) layer

    **With a reference:**
    - The RQ1 Siamese CNN performs real forgery detection
    - Genuine signatures → high AI score (~94-100%)
    - Forged signatures → low AI score (~60-70%)

    **⚠️ Use the same reference signature that was used when the document was issued.**
    """)

ref_file = st.file_uploader(
    "Upload reference signature",
    type=["png", "jpg", "jpeg"],
    key="verify_ref",
    help="The original genuine signature — used by AI to compare against the test signature.",
)
if ref_file:
    st.image(ref_file, caption="Reference preview", use_container_width=True)

# ============================================================
# SUBMIT
# ============================================================
st.divider()

if st.button("🔍 Verify Document", type="primary", use_container_width=True):
    if not doc_file or not sig_file:
        st.error("⚠️ Please upload both the document AND the signature.")
    else:
        with st.spinner("Running hybrid verification (crypto + AI + fusion)..."):
            files = {
                "document": (doc_file.name, doc_file.getvalue(), doc_file.type or "image/png"),
                "signature": (sig_file.name, sig_file.getvalue(), sig_file.type or "image/png"),
            }
            # Add reference signature if provided (for AI comparison)
            if ref_file:
                files["reference"] = (ref_file.name, ref_file.getvalue(), ref_file.type or "image/png")

            try:
                r = requests.post(f"{HYBRID_API}/verify", files=files, timeout=60)
                if r.status_code == 200:
                    st.session_state["verify_result"] = r.json()
                else:
                    st.error(f"❌ Failed: {r.status_code} — {r.text}")
            except Exception as e:
                st.error(f"❌ Request failed: {e}")

# ============================================================
# DISPLAY RESULT
# ============================================================
if "verify_result" in st.session_state:
    result = st.session_state["verify_result"]

    st.divider()
    st.subheader("📊 Verification Verdict")

    # Color-coded banner
    path = result["decision_path"]
    if result["is_authentic"]:
        st.success(f"✅ **AUTHENTIC** — Decision: `{path}`")
    elif result["tamper_detected"]:
        st.error(f"🚨 **TAMPERED** — Decision: `{path}`")
    else:
        st.warning(f"⚠️ **SUSPICIOUS** — Decision: `{path}`")

    # Metrics
    col_a, col_b, col_c, col_d = st.columns(4)
    with col_a:
        st.metric("Confidence", f"{result['confidence']:.1%}")
    with col_b:
        st.metric("AI Score", f"{result['ai_score']:.1%}")
    with col_c:
        st.metric("Crypto Score", f"{result['crypto_score']:.1%}")
    with col_d:
        st.metric("Tamper", "🚨 YES" if result["tamper_detected"] else "✅ NO")

    if result.get("document_id"):
        st.info(f"📄 Document ID: **{result['document_id']}**")

    # Detailed explanations
    with st.expander("🔬 Detailed Explanations (Click to expand)"):
        st.json(result["explanations"])

st.divider()
st.caption("SigGuard LK — RQ3 Hybrid Verification · MSc Research")