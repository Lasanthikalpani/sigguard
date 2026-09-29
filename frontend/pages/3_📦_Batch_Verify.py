"""
RQ3 Frontend — Page 3: Batch Verification

Upload multiple document+signature pairs and verify them all at once.
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"
HYBRID_API = f"{API_URL}/api/v1/hybrid"

st.set_page_config(page_title="Batch Verify — SigGuard LK", page_icon="📦", layout="wide")

st.title("📦 Batch Document Verification")
st.markdown("""
Verify **up to 50 document + signature pairs** at once.

⚠️ Ensure documents are paired in the correct order:
- Document 1 ↔ Signature 1
- Document 2 ↔ Signature 2
- etc.
""")

st.divider()

col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 Documents")
    docs = st.file_uploader(
        "Upload documents (multiple)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="batch_docs",
    )
    if docs:
        st.write(f"**{len(docs)} document(s) uploaded:**")
        for d in docs:
            st.caption(f"• {d.name} ({len(d.getvalue()):,} bytes)")

with col2:
    st.subheader("✍️ Signatures")
    sigs = st.file_uploader(
        "Upload signatures (multiple)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        key="batch_sigs",
    )
    if sigs:
        st.write(f"**{len(sigs)} signature(s) uploaded:**")
        for s in sigs:
            st.caption(f"• {s.name} ({len(s.getvalue()):,} bytes)")

st.divider()

if st.button("🚀 Verify All", type="primary", width='stretch'):
    if not docs or not sigs:
        st.error("⚠️ Please upload both documents and signatures.")
    elif len(docs) != len(sigs):
        st.error(f"⚠️ Count mismatch: {len(docs)} documents vs {len(sigs)} signatures.")
    else:
        with st.spinner(f"Verifying {len(docs)} document(s)..."):
            files = []
            for d, s in zip(docs, sigs):
                files.append(("documents", (d.name, d.getvalue(), d.type or "image/png")))
                files.append(("signatures", (s.name, s.getvalue(), s.type or "image/png")))
            
            try:
                r = requests.post(f"{HYBRID_API}/verify-batch", files=files, timeout=120)
                if r.status_code == 200:
                    st.session_state["batch_result"] = r.json()
                else:
                    st.error(f"❌ Batch verify failed: {r.status_code} — {r.text}")
            except Exception as e:
                st.error(f"❌ Request failed: {e}")

if "batch_result" in st.session_state:
    batch = st.session_state["batch_result"]
    
    st.divider()
    st.subheader("📊 Batch Results")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total", batch["total"])
    with col2:
        st.metric("✅ Authentic", batch["authentic"])
    with col3:
        st.metric("🚨 Tampered", batch["tampered"])
    
    st.divider()
    st.subheader("Detailed Results")
    for r in batch["results"]:
        icon = "✅" if r.get("is_authentic") else "🚨" if r.get("tamper_detected") else "⚠️"
        with st.expander(f"{icon} {r['file']} — {r.get('decision_path', 'ERROR')}"):
            st.json(r)

st.divider()
st.caption("SigGuard LK — RQ3 Hybrid Verification · MSc Research · University of Sri Jayewardenepura")