"""
RQ3 Page 11 — LAYER 4: RSA Digital Signature

Theory (SigVerify paper):
- Digital Signature = Document's digital royal seal
- Created with Private Key (issuer only)
- Verified with Public Key (shared)
- 100% tamper detection via Avalanche Effect
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.services.rsa_service import RSAService

st.set_page_config(
    page_title="Layer 4: RSA Signature — SigVerify",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 LAYER 4: RSA Digital Signature")
st.markdown("""
**The Digital Royal Seal of a Document**

A digital signature is created with a **Private Key** and verified with a **Public Key**.
Without it, the document is not legally valid.
""")

st.divider()

# ============================================================
# KEY STATUS
# ============================================================
st.subheader("🔑 Government Office Keys")

try:
    rsa = RSAService()
    info = rsa.get_key_info()

    col1, col2 = st.columns(2)

    with col1:
        if info["private_key_exists"]:
            st.success(f"""
            **🔒 PRIVATE KEY** (Secret)

            - Location: `{info['private_key_path']}`
            - Purpose: Sign documents
            - Visibility: **TOP SECRET**
            - Key size: {info.get('key_size', 'N/A')} bits
            """)
        else:
            st.error("❌ Private key not found")

    with col2:
        if info["public_key_exists"]:
            st.success(f"""
            **🔓 PUBLIC KEY** (Shared)

            - Location: `{info['public_key_path']}`
            - Purpose: Verify signatures
            - Visibility: **PUBLIC**
            - Shared with: Everyone
            """)
        else:
            st.error("❌ Public key not found")

    if not info["private_key_exists"] or not info["public_key_exists"]:
        st.warning("Run: `python scripts/generate_rsa_keys.py` to generate keys")
        st.stop()

except Exception as e:
    st.error(f"❌ RSA service error: {e}")
    st.info("Run: `python scripts/generate_rsa_keys.py` first")
    st.stop()

st.divider()

# ============================================================
# SIGN DOCUMENT
# ============================================================
st.subheader("✍️ Step 1: Sign Document (Issuer)")

st.markdown("Enter content_hash and metadata_hash to sign:")

col1, col2 = st.columns(2)
with col1:
    content_hash = st.text_input(
        "Content Hash (SHA-256, 64 chars)",
        value="028826135b243c7dbbb48395d67e92fe" + "0" * 32,
    )
with col2:
    metadata_hash = st.text_input(
        "Metadata Hash (SHA-256, 64 chars)",
        value="573e4be49b2911c75db16e79ecc31b3d" + "0" * 32,
    )

if st.button("🔒 Sign Document", type="primary", use_container_width=True):
    if len(content_hash) != 64 or len(metadata_hash) != 64:
        st.error("Both hashes must be 64 characters (SHA-256 hex)")
    else:
        signed = rsa.sign_document(content_hash, metadata_hash)

        st.success("✅ Document signed successfully!")

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Combined Hash", signed["combined_hash"][:16] + "...")
        with col2:
            st.metric("Algorithm", signed["algorithm"])

        with st.expander("🔍 Full Signature Data"):
            st.json(signed)

        st.session_state["rsa_signed"] = signed
        st.session_state["rsa_content_hash"] = content_hash
        st.session_state["rsa_metadata_hash"] = metadata_hash

st.divider()

# ============================================================
# VERIFY DOCUMENT
# ============================================================
st.subheader("🔍 Step 2: Verify Document (Officer)")

if "rsa_signed" not in st.session_state:
    st.info("ℹ️ Please sign a document first (Step 1).")
else:
    signed = st.session_state["rsa_signed"]
    original_content = st.session_state["rsa_content_hash"]
    original_metadata = st.session_state["rsa_metadata_hash"]

    st.markdown("**Test verification with original or tampered hashes:**")

    col1, col2 = st.columns(2)
    with col1:
        test_content = st.text_input(
            "Test Content Hash",
            value=original_content,
            key="test_content",
        )
    with col2:
        test_metadata = st.text_input(
            "Test Metadata Hash",
            value=original_metadata,
            key="test_metadata",
        )

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("✅ Verify Original", use_container_width=True):
            result = rsa.verify_document(
                test_content, test_metadata, signed["signature"]
            )
            if result["valid"]:
                st.success("✅ SIGNATURE VALID — Document is authentic")
            else:
                st.error(f"❌ SIGNATURE INVALID — {result['reason']}")

    with col_btn2:
        if st.button("🚨 Verify Tampered", use_container_width=True):
            tampered = "x" * 64
            result = rsa.verify_document(
                tampered, original_metadata, signed["signature"]
            )
            if result["valid"]:
                st.warning("⚠️ Signature passed?!")
            else:
                st.error(f"🚨 TAMPERED — {result['reason']}")

st.divider()
st.caption("SigVerify — LAYER 4: RSA Digital Signature · MSc Research · University of Sri Jayewardenepura")