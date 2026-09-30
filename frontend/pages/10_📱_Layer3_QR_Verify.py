"""
RQ3 Page 10 — LAYER 3: QR Code Verification (SigVerify Theory)

6-step verification:
1. SCAN QR Code
2. Verify CONTENT HASH
3. Verify METADATA HASH
4. Verify SIGNATURE
5. Check BLOCKCHAIN
6. FINAL DECISION

4 Scenarios:
- FULLY_AUTHENTIC
- TAMPERED
- METADATA_MODIFIED
- AUTHENTIC_NOT_IN_BLOCKCHAIN
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.services.qr_service import QRVerificationLayer
from src.api.services.blockchain_service import get_ledger

st.set_page_config(
    page_title="Layer 3: QR Verification — SigVerify",
    page_icon="📱",
    layout="wide",
)

st.title("📱 LAYER 3: QR Code Verification")
st.markdown("""
**SigVerify — 6-step verification process**

The QR code is the digital identity of the document.
It contains 6 fields that allow instant verification.
""")

st.divider()

# ============================================================
# QR DATA STRUCTURE
# ============================================================
with st.expander("📋 What Does the QR Code Contain? (6 Fields)"):
    st.markdown("""
    | Field | Purpose |
    |-------|---------|
    | **content_hash** | SHA-256 of document content |
    | **metadata_hash** | SHA-256 of (timestamp + issuer + doc_id) |
    | **signature** | RSA/HMAC signature from issuer |
    | **timestamp** | Issue date/time |
    | **issuer** | Issuing authority |
    | **document_id** | Unique document ID |
    """)

# ============================================================
# UPLOAD
# ============================================================
st.subheader("📤 Upload Document with QR")

uploaded = st.file_uploader(
    "Choose document image",
    type=["png", "jpg", "jpeg"],
    key="layer3_upload",
)
if uploaded:
    st.image(uploaded, caption="Document uploaded", use_container_width=True)

# ============================================================
# VERIFY BUTTON
# ============================================================
if st.button("📱 Verify with Layer 3", type="primary", use_container_width=True, disabled=uploaded is None):
    with st.spinner("Running 6-step QR verification..."):
        try:
            layer3 = QRVerificationLayer()
            ledger = get_ledger()
            result = layer3.verify_document(
                uploaded.getvalue(),
                blockchain_ledger=ledger,
            )
            st.session_state["layer3_result"] = result
        except Exception as e:
            st.error(f"❌ Verification error: {e}")

# ============================================================
# RESULT
# ============================================================
if "layer3_result" in st.session_state:
    result = st.session_state["layer3_result"]
    status = result["status"]
    display = QRVerificationLayer.status_display(status)

    st.divider()
    st.subheader("📋 Layer 3 Result")

    # ---------- Verdict Banner ----------
    if status == "FULLY_AUTHENTIC":
        st.success(f"""
        # {display['emoji']} {display['title']}
        
        **{display['message']}**
        """)
    elif status in ("TAMPERED", "QR_MISSING"):
        st.error(f"""
        # {display['emoji']} {display['title']}
        
        **{display['message']}**
        """)
    else:
        st.warning(f"""
        # {display['emoji']} {display['title']}
        
        **{display['message']}**
        """)

    # ---------- 6-Step Checklist ----------
    st.markdown("### 🔍 6-Step Verification Checklist")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if result["content_hash_match"]:
            st.success("✅ **CONTENT HASH**\n\nMatched")
        else:
            st.error("❌ **CONTENT HASH**\n\nMISMATCH")

    with col2:
        if result["metadata_hash_match"]:
            st.success("✅ **METADATA HASH**\n\nMatched")
        else:
            st.error("❌ **METADATA HASH**\n\nMISMATCH")

    with col3:
        if result["signature_valid"]:
            st.success("✅ **SIGNATURE**\n\nValid")
        else:
            st.error("❌ **SIGNATURE**\n\nInvalid")

    with col4:
        if result["blockchain_found"]:
            st.success("✅ **BLOCKCHAIN**\n\nFound")
        else:
            st.warning("⚠️ **BLOCKCHAIN**\n\nNot Found")

    # ---------- Details ----------
    st.markdown("### 📋 Details")

    details = result.get("details", {})
    st.json(details)

    # ---------- QR Raw Data ----------
    with st.expander("📱 QR Raw Data (6 Fields)"):
        if result.get("qr_data"):
            st.json(result["qr_data"])
        else:
            st.info("No QR data available")

st.divider()
st.caption("SigVerify — LAYER 3 · MSc Research · University of Sri Jayewardenepura")