"""
RQ3 Layer 5 — Document Amendment (Streamlit UI).

Three tabs:
  1. Issue Amendment   — issue an amended document
  2. Verify Amendment  — verify an (possibly amended) document
  3. Lineage Viewer    — view the lineage of a document
"""
import base64
import io
import json
from datetime import datetime

import requests
import streamlit as st
from PIL import Image

API = "http://localhost:8000"

st.set_page_config(
    page_title="Layer 5 — Document Amendment",
    page_icon="📝",
    layout="wide",
)

st.title("📝 Layer 5 — Document Amendment")
st.caption("RQ3 — Legitimate change management with cryptographic lineage")

# ------------------------------------------------------------
# Sidebar — API health
# ------------------------------------------------------------
with st.sidebar:
    st.header("API Status")
    try:
        h = requests.get(f"{API}/api/v1/amendment/health", timeout=3).json()
        st.success(f"✅ {h['status']}")
        st.caption(f"Service: {h['service']}")
    except Exception as e:
        st.error(f"❌ API not reachable: {e}")
        st.stop()

    st.markdown("---")
    st.header("Supported reasons")
    try:
        r = requests.get(f"{API}/api/v1/amendment/reasons", timeout=3).json()
        for key, label in r["supported"].items():
            st.caption(f"• `{key}` — {label}")
    except Exception as e:
        st.warning(f"Could not load reasons: {e}")


# ------------------------------------------------------------
# Tabs
# ------------------------------------------------------------
tab_issue, tab_verify, tab_lineage = st.tabs([
    "🆕 Issue Amendment",
    "🔍 Verify Amendment",
    "🌳 Lineage Viewer",
])


# ============================================================
# TAB 1 — Issue Amendment
# ============================================================
with tab_issue:
    st.header("Issue an Amended Document")
    st.info(
        "Upload the **original document** (already issued with a QR code) "
        "and the **new content + signature**. The API will generate a "
        "new QR and record the amendment in the blockchain."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("1️⃣ New document content")
        new_doc_file = st.file_uploader(
            "New document image (PNG/JPEG)",
            type=["png", "jpg", "jpeg"],
            key="issue_new_doc",
        )
        if new_doc_file:
            st.image(new_doc_file, caption="New content", use_container_width=True)

    with col2:
        st.subheader("2️⃣ New signature region")
        new_sig_file = st.file_uploader(
            "New signature image",
            type=["png", "jpg", "jpeg"],
            key="issue_new_sig",
        )
        if new_sig_file:
            st.image(new_sig_file, caption="New signature", use_container_width=True)

    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        original_doc_id = st.text_input(
            "Original document ID",
            placeholder="e.g. LK-20261001-A282CF67",
            help="The doc_id of the existing document to amend",
        )
        amendment_reason = st.selectbox(
            "Amendment reason",
            options=[
                "surname_change",
                "address_change",
                "date_correction",
                "info_addition",
                "error_correction",
            ],
        )

    with col4:
        issuer = st.text_input("Issuer", value="Registrar General's Office")
        evidence_text = st.text_input(
            "Evidence (optional)",
            placeholder='{"marriage_cert": "MC-2026-001"}',
            help="Optional JSON evidence",
        )

    if st.button("🚀 Issue Amendment", type="primary", use_container_width=True):
        if not new_doc_file or not new_sig_file or not original_doc_id:
            st.error("Please fill in all required fields.")
        else:
            with st.spinner("Issuing amendment ..."):
                try:
                    files = {
                        "new_document": (
                            new_doc_file.name,
                            new_doc_file.getvalue(),
                            "image/png",
                        ),
                        "new_signature": (
                            new_sig_file.name,
                            new_sig_file.getvalue(),
                            "image/png",
                        ),
                    }
                    data = {
                        "original_doc_id": original_doc_id,
                        "amendment_reason": amendment_reason,
                        "issuer": issuer,
                    }
                    if evidence_text:
                        data["evidence_json"] = evidence_text

                    r = requests.post(
                        f"{API}/api/v1/amendment/amend",
                        files=files,
                        data=data,
                        timeout=60,
                    )

                    if r.status_code == 200:
                        result = r.json()
                        st.success("✅ Amendment issued!")
                        st.balloons()

                        col_a, col_b = st.columns(2)

                        with col_a:
                            st.metric("Amended doc ID", result["amended_doc_id"])
                            st.metric("Original doc ID", result["original_doc_id"])
                            st.metric("Reason", result["amendment_reason_display"])
                            st.metric("Block index", result["blockchain"]["block_index"])

                        with col_b:
                            st.markdown("**Blockchain block hash**")
                            st.code(result["blockchain"]["block_hash"], language="text")

                        # Show stamped document
                        stamped_bytes = base64.b64decode(
                            result["stamped_document_base64"]
                        )
                        st.subheader("Stamped document (with new QR)")
                        st.image(stamped_bytes, use_container_width=True)

                        # Download button
                        st.download_button(
                            "⬇️ Download amended document",
                            data=stamped_bytes,
                            file_name=f"{result['amended_doc_id']}.png",
                            mime="image/png",
                        )

                        with st.expander("Full JSON response"):
                            st.json(result)
                    else:
                        st.error(f"HTTP {r.status_code}: {r.text}")
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 2 — Verify Amendment
# ============================================================
with tab_verify:
    st.header("Verify an Amended Document")
    st.info(
        "Upload a document (original or amended). The system will decode "
        "the QR and tell you if it is **FULLY_AUTHENTIC**, "
        "**AMENDED_AUTHENTIC**, or **TAMPERED**."
    )

    verify_file = st.file_uploader(
        "Document to verify (PNG/JPEG)",
        type=["png", "jpg", "jpeg"],
        key="verify_doc",
    )

    if verify_file:
        st.image(verify_file, caption="Document to verify", use_container_width=True)

    if st.button("🔍 Verify", type="primary", use_container_width=True):
        if not verify_file:
            st.error("Please upload a document.")
        else:
            with st.spinner("Verifying ..."):
                try:
                    r = requests.post(
                        f"{API}/api/v1/amendment/verify",
                        files={
                            "document": (
                                verify_file.name,
                                verify_file.getvalue(),
                                "image/png",
                            ),
                        },
                        timeout=60,
                    )
                    if r.status_code != 200:
                        st.error(f"HTTP {r.status_code}: {r.text}")
                    else:
                        result = r.json()
                        status = result["status"]

                        if status == "FULLY_AUTHENTIC":
                            st.success(f"✅ {status} — Original document, all checks pass")
                        elif status == "AMENDED_AUTHENTIC":
                            st.success(f"✅ {status} — Legitimate amendment recognized")
                        elif status == "TAMPERED":
                            st.error(f"🚨 {status} — Document has been modified")
                        elif status == "METADATA_MODIFIED":
                            st.warning(f"⚠️ {status} — Metadata has changed")
                        elif status == "QR_MISSING":
                            st.error(f"🚨 {status} — No QR code found")
                        else:
                            st.info(f"Status: {status}")

                        st.markdown("### Details")
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Status", status)
                            st.metric("Document ID", result.get("document_id") or "—")

                        with col2:
                            bc = result.get("blockchain")
                            if bc:
                                st.metric("Is amendment?", bc.get("is_amendment"))
                                st.metric("Original doc", bc.get("original_doc_id") or "—")
                                st.metric("Reason", bc.get("amendment_reason") or "—")

                        with st.expander("Full JSON response"):
                            st.json(result)

                        # Show lineage if amendment
                        if result.get("lineage"):
                            st.markdown("### Lineage")
                            for block in result["lineage"]:
                                marker = (
                                    "🔹 AMENDMENT"
                                    if block.get("metadata", {}).get("is_amendment")
                                    else "🔸 ORIGINAL"
                                )
                                st.markdown(f"**{marker}** — `{block['doc_id']}`")
                                with st.expander(f"Block {block['index']}"):
                                    st.json(block)
                except Exception as e:
                    st.error(f"Error: {e}")


# ============================================================
# TAB 3 — Lineage Viewer
# ============================================================
with tab_lineage:
    st.header("Lineage Viewer")
    st.info(
        "Enter a document ID to see its full history: original + all amendments."
    )

    lineage_doc_id = st.text_input(
        "Document ID",
        placeholder="e.g. LK-20261001-A282CF67-AMD-001",
        key="lineage_doc_id",
    )

    if st.button("🌳 View Lineage", type="primary", use_container_width=True):
        if not lineage_doc_id:
            st.error("Please enter a document ID.")
        else:
            with st.spinner("Loading lineage ..."):
                try:
                    r = requests.get(
                        f"{API}/api/v1/amendment/lineage/{lineage_doc_id}",
                        timeout=10,
                    )
                    if r.status_code != 200:
                        st.error(f"HTTP {r.status_code}: {r.text}")
                    else:
                        result = r.json()
                        st.metric("Lineage length", result["lineage_length"])

                        for i, block in enumerate(result["lineage"]):
                            meta = block.get("metadata", {})
                            is_amend = meta.get("is_amendment", False)

                            if is_amend:
                                label = f"🔹 Amendment {i} — `{block['doc_id']}`"
                                st.markdown(f"### {label}")
                                st.caption(
                                    f"Reason: {meta.get('amendment_reason')} | "
                                    f"Original: {meta.get('original_doc_id')}"
                                )
                            else:
                                st.markdown(f"### 🔸 Original — `{block['doc_id']}`")
                                st.caption(f"Issued: {block.get('issued_at')}")

                            with st.expander("Block details"):
                                st.json(block)
                except Exception as e:
                    st.error(f"Error: {e}")


# ------------------------------------------------------------
# Footer
# ------------------------------------------------------------
st.markdown("---")
st.caption(
    "SigVerify RQ3 — Layer 5: Document Amendment | "
    "University of Sri Jayewardenepura | MSc in Computer Science"
)