"""
RQ3 Layer 6 — Copy vs Original (Streamlit UI).

Three tabs:
  1. Issue Certified Copy  — registry-issued copy of a document
  2. Classify Document     — is it original / certified / photocopy / forged?
  3. Document Types        — explanation of the 4 types
"""
import base64
import requests
import streamlit as st

API = "http://localhost:8000"

st.set_page_config(
    page_title="Layer 6 — Copy vs Original",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Layer 6 — Copy vs Original")
st.caption("RQ3 — Distinguish original, certified copy, photocopy, and forgery")

# Sidebar
with st.sidebar:
    st.header("API Status")
    try:
        h = requests.get(f"{API}/api/v1/copy/health", timeout=3).json()
        st.success(f"✅ {h['status']}")
    except Exception as e:
        st.error(f"❌ API not reachable: {e}")
        st.stop()

    st.markdown("---")
    st.header("Document types")
    try:
        r = requests.get(f"{API}/api/v1/copy/types", timeout=3).json()
        for key, desc in r["supported"].items():
            st.caption(f"**{key}** — {desc}")
    except Exception:
        pass


tab_issue, tab_classify, tab_types = st.tabs([
    "🆕 Issue Certified Copy",
    "🔍 Classify Document",
    "📖 Document Types",
])


# ============================================================
# TAB 1 — Issue Certified Copy
# ============================================================
with tab_issue:
    st.header("Issue a Certified Copy")
    st.info(
        "Enter the doc_id of an existing registered document. The system will "
        "create a **certified copy** with a new QR code, new timestamp, and a "
        "blockchain entry linking it to the original."
    )

    col1, col2 = st.columns(2)
    with col1:
        original_doc_id = st.text_input(
            "Original document ID",
            placeholder="e.g. LK-20261001-XXXXXXXX",
        )
        certifier = st.text_input(
            "Certifier",
            value="Registrar General's Office",
        )
    with col2:
        reason = st.text_input(
            "Reason",
            value="certified_copy_request",
        )

    if st.button("🚀 Issue Certified Copy", type="primary", use_container_width=True):
        if not original_doc_id:
            st.error("Please enter the original document ID.")
        else:
            with st.spinner("Issuing certified copy ..."):
                try:
                    r = requests.post(
                        f"{API}/api/v1/copy/issue-certified",
                        data={
                            "original_doc_id": original_doc_id,
                            "certifier": certifier,
                            "reason": reason,
                        },
                        timeout=60,
                    )
                    if r.status_code == 200:
                        result = r.json()
                        st.success("✅ Certified copy issued!")
                        st.balloons()

                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.metric("Certified copy ID", result["certified_copy_id"])
                            st.metric("Original doc ID", result["original_doc_id"])
                            st.metric("Certifier", result["certifier"])
                            st.metric("Block index", result["blockchain"]["block_index"])
                        with col_b:
                            st.markdown("**Blockchain block hash**")
                            st.code(result["blockchain"]["block_hash"], language="text")

                        # Show QR
                        qr_bytes = base64.b64decode(result["new_qr_base64"])
                        st.subheader("New QR code")
                        st.image(qr_bytes, width=300)

                        st.download_button(
                            "⬇️ Download QR",
                            data=qr_bytes,
                            file_name=f"{result['certified_copy_id']}_qr.png",
                            mime="image/png",
                        )

                        with st.expander("Full JSON response"):
                            st.json(result)
                    else:
                        st.error(f"HTTP {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 2 — Classify Document
# ============================================================
with tab_classify:
    st.header("Classify a Document")
    st.info(
        "Upload a document. The system will tell you whether it is an "
        "**ORIGINAL**, **CERTIFIED COPY**, **PHOTOCOPY**, or **FORGED COPY**."
    )

    classify_file = st.file_uploader(
        "Document to classify",
        type=["png", "jpg", "jpeg"],
        key="classify_doc",
    )

    if classify_file:
        st.image(classify_file, caption="Document to classify", use_container_width=True)

    if st.button("🔍 Classify", type="primary", use_container_width=True):
        if not classify_file:
            st.error("Please upload a document.")
        else:
            with st.spinner("Classifying ..."):
                try:
                    r = requests.post(
                        f"{API}/api/v1/copy/classify",
                        files={
                            "document": (
                                classify_file.name,
                                classify_file.getvalue(),
                                "image/png",
                            ),
                        },
                        timeout=60,
                    )
                    if r.status_code != 200:
                        st.error(f"HTTP {r.status_code}: {r.text}")
                    else:
                        result = r.json()
                        dtype = result.get("document_type", "UNKNOWN")

                        # Emoji by type
                        emoji_map = {
                            "ORIGINAL": "🟢",
                            "CERTIFIED_COPY": "🔵",
                            "PHOTOCOPY": "🟡",
                            "AMENDMENT": "🟣",
                            "TAMPERED": "🔴",
                            "QR_MISSING": "⚫",
                            "UNKNOWN": "⚪",
                        }
                        emoji = emoji_map.get(dtype, "❓")

                        if dtype == "ORIGINAL":
                            st.success(f"{emoji} {dtype} — Registry-issued original document")
                        elif dtype == "CERTIFIED_COPY":
                            st.success(f"{emoji} {dtype} — Registry-issued certified copy")
                        elif dtype == "PHOTOCOPY":
                            st.warning(f"{emoji} {dtype} — Simple photocopy (not original)")
                        elif dtype == "AMENDMENT":
                            st.info(f"{emoji} {dtype} — Legitimate amendment")
                        elif dtype == "TAMPERED":
                            st.error(f"{emoji} {dtype} — Content or QR modified")
                        elif dtype == "QR_MISSING":
                            st.error(f"{emoji} {dtype} — No QR found")
                        else:
                            st.info(f"{emoji} {dtype}")

                        st.markdown("### Details")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("Document type", dtype)
                            st.metric("Document ID", result.get("document_id") or "—")
                            st.metric("HMAC valid", result.get("hmac_valid"))
                        with col2:
                            st.metric("Content hash match", result.get("content_hash_match"))
                            st.metric("In ledger", result.get("in_ledger"))
                            st.metric("Original doc", result.get("original_doc_id") or "—")

                        st.markdown("**Explanation**")
                        st.info(result.get("explanation", "—"))

                        with st.expander("Full JSON response"):
                            st.json(result)
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 3 — Document Types
# ============================================================
with tab_types:
    st.header("The 4 Document Types")
    st.markdown(
        """
### 🟢 ORIGINAL

- **Content hash:** Original
- **Metadata hash:** Original
- **Timestamp:** Original
- **QR:** Original QR
- **Status:** `ORIGINAL`

Issued by the registry, recorded in the blockchain.

---

### 🔵 CERTIFIED COPY

- **Content hash:** Same as original
- **Metadata hash:** **New** (new timestamp)
- **Timestamp:** **New**
- **QR:** **New QR**
- **Status:** `CERTIFIED_COPY`

Registry-issued copy. The information is identical, but the issuance event is new.
Recorded in the blockchain with `is_certified_copy=True`.

---

### 🟡 PHOTOCOPY

- **Content hash:** Same as original
- **Metadata hash:** Same as original
- **Timestamp:** Original
- **QR:** Original QR (copied)
- **Status:** `PHOTOCOPY`

A simple photocopy — the QR is copied, not re-issued. **Not a legal original.**

---

### 🔴 FORGED COPY

- **Content hash:** **Changed**
- **Metadata hash:** Original (copied)
- **Timestamp:** Original (copied)
- **QR:** Original QR (copied)
- **Status:** `TAMPERED`

A fraud: the QR belongs to a real document, but the content has been modified.

---

### Why Layer 6 matters

Without Layer 6, a forged photocopy passes all cryptographic checks
(content hash matches, HMAC matches) — because the QR is genuine.
The system cannot tell it apart from the original.

Layer 6 uses the **blockchain ledger** to identify whether a given
`doc_id` is an original, a certified copy, or unregistered — and
detects forgeries via content-hash mismatch.
        """
    )


# Footer
st.markdown("---")
st.caption(
    "SigVerify RQ3 — Layer 6: Copy vs Original | "
    "University of Sri Jayewardenepura | MSc in Computer Science"
)
