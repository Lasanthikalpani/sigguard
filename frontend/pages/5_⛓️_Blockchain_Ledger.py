"""
RQ3 Page 5 — Blockchain Ledger Explorer

Interactive UI for:
- Viewing ledger statistics
- Verifying chain integrity
- Looking up documents by doc_id
- Issuing certified copies
- Finding documents by content hash
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"
LEDGER_API = f"{API_URL}/api/v1/hybrid/ledger"

st.set_page_config(
    page_title="Blockchain Ledger — SigGuard LK",
    page_icon="⛓️",
    layout="wide",
)

st.title("⛓️ Blockchain Document Ledger")
st.markdown("""
**RQ3 — Supervisor's Novelty: Document-Wise Blockchain Ledger**

This page demonstrates the blockchain ledger that:
- Stores each document as a block (immutable)
- Supports **certified copies** (same content, new timestamp)
- Scales to millions of documents (e.g., 1980 birth certificates)
""")

st.divider()

# API health check
try:
    health = requests.get(f"{API_URL}/api/v1/hybrid/health", timeout=3).json()
    if health.get("status") != "healthy":
        st.warning("⚠️ API not fully healthy")
    else:
        st.success("✅ API is healthy")
except Exception:
    st.error(f"❌ Cannot connect to API at {API_URL}")
    st.info("**Start the API:**\n```\nconda activate sigguard\npython -m uvicorn src.api.main:app --reload\n```")
    st.stop()

st.divider()

# ============================================================
# TABS
# ============================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Ledger Stats",
    "🔍 Lookup Document",
    "📋 Find by Hash",
    "📜 Certified Copy",
    "✅ Verify Chain",
])

# ============================================================
# TAB 1: LEDGER STATS
# ============================================================
with tab1:
    st.subheader("📊 Ledger Statistics")
    st.caption("Overview of the entire blockchain ledger.")

    if st.button("🔄 Refresh", key="refresh_stats"):
        st.rerun()

    try:
        r = requests.get(f"{LEDGER_API}/stats", timeout=5)
        if r.status_code == 200:
            stats = r.json()["stats"]
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Blocks", stats["total_blocks"])
            with col2:
                st.metric("Latest Index", stats["latest_index"])
            with col3:
                st.metric("Genesis Hash", stats["genesis_hash"][:16] + "...")
            st.json(stats)
        else:
            st.error(f"Failed: {r.status_code}")
    except Exception as e:
        st.error(f"Error: {e}")

# ============================================================
# TAB 2: LOOKUP DOCUMENT
# ============================================================
with tab2:
    st.subheader("🔍 Lookup Document by ID")
    st.caption("Enter a Document ID to view its blockchain block.")

    doc_id = st.text_input("Document ID", key="lookup_doc_id", placeholder="LK-20260929-XXXXXXXX")

    if st.button("🔍 Lookup", key="lookup_btn"):
        if not doc_id:
            st.warning("Please enter a Document ID")
        else:
            try:
                r = requests.post(
                    f"{LEDGER_API}/lookup",
                    json={"doc_id": doc_id},
                    timeout=5,
                )
                if r.status_code == 200:
                    block = r.json()["block"]
                    st.success(f"✅ Found: {block['doc_id']}")
                    st.json(block)
                elif r.status_code == 404:
                    st.warning(f"Document not found: {doc_id}")
                else:
                    st.error(f"Failed: {r.status_code} — {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================
# TAB 3: FIND BY HASH
# ============================================================
with tab3:
    st.subheader("📋 Find Documents by Content Hash")
    st.caption("Content hash is SAME for original + certified copies. Find all versions.")

    content_hash = st.text_input("Content Hash (SHA-256, 64 chars)", key="find_hash")

    if st.button("🔍 Find", key="find_btn"):
        if not content_hash or len(content_hash) != 64:
            st.warning("Please enter a valid 64-character SHA-256 hash")
        else:
            try:
                r = requests.get(
                    f"{LEDGER_API}/find-by-hash",
                    params={"content_hash": content_hash},
                    timeout=5,
                )
                if r.status_code == 200:
                    result = r.json()
                    st.success(f"✅ Found {result['matches']} matching block(s)")
                    for block in result["blocks"]:
                        is_copy = block.get("metadata", {}).get("is_certified_copy", False)
                        label = "COPY" if is_copy else "ORIGINAL"
                        with st.expander(f"[{label}] {block['doc_id']}"):
                            st.json(block)
                else:
                    st.error(f"Failed: {r.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================
# TAB 4: CERTIFIED COPY (Supervisor's key insight!)
# ============================================================
with tab4:
    st.subheader("📜 Issue Certified Copy")
    st.markdown("""
    **Supervisor's Key Insight:**
    
    A certified copy has the **SAME content hash** as the original,
    but a **DIFFERENT timestamp**. This is NOT a forgery.
    """)

    original_doc_id = st.text_input("Original Document ID", key="cert_original")
    certifier = st.text_input("Certifier", value="Government of Sri Lanka", key="cert_certifier")

    if st.button("📜 Issue Certified Copy", key="cert_btn", type="primary"):
        if not original_doc_id:
            st.warning("Please enter the original Document ID")
        else:
            try:
                r = requests.post(
                    f"{LEDGER_API}/certified-copy",
                    json={
                        "original_doc_id": original_doc_id,
                        "certifier": certifier,
                    },
                    timeout=5,
                )
                if r.status_code == 200:
                    result = r.json()
                    copy_block = result["certified_copy"]
                    st.success(f"✅ Certified copy issued: {copy_block['doc_id']}")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Original ID", original_doc_id)
                        st.metric("Content Hash", copy_block["content_hash"][:16] + "...")
                    with col2:
                        st.metric("Certified ID", copy_block["doc_id"])
                        st.metric("New Timestamp", copy_block["issued_at"][:19])
                    
                    st.info("""
                    **Why NOT a forgery:**
                    - Content hash: **SAME** as original
                    - Timestamp: **DIFFERENT** (legitimate re-issuance)
                    """)
                    st.json(copy_block)
                elif r.status_code == 404:
                    st.warning(f"Original not found: {original_doc_id}")
                else:
                    st.error(f"Failed: {r.status_code} — {r.text}")
            except Exception as e:
                st.error(f"Error: {e}")

# ============================================================
# TAB 5: VERIFY CHAIN
# ============================================================
with tab5:
    st.subheader("✅ Verify Blockchain Integrity")
    st.caption("Checks if the entire chain is intact (no tampering).")

    if st.button("🔍 Verify Chain", key="verify_btn", type="primary"):
        try:
            r = requests.get(f"{LEDGER_API}/verify-chain", timeout=5)
            if r.status_code == 200:
                result = r.json()
                if result["valid"]:
                    st.success(f"✅ Chain is VALID — {result['length']} blocks")
                else:
                    st.error(f"🚨 Chain is INVALID — {len(result['errors'])} error(s)")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Valid", str(result["valid"]))
                with col2:
                    st.metric("Length", result["length"])
                
                if result["errors"]:
                    for err in result["errors"]:
                        st.code(err)
                st.json(result)
            else:
                st.error(f"Failed: {r.status_code}")
        except Exception as e:
            st.error(f"Error: {e}")

# Sidebar info
st.sidebar.markdown("""
### ⛓️ Ledger Info
- **Storage:** `data/blockchain/ledger.json`
- **Structure:** Linked blocks (prev_hash)
- **Immutability:** Append-only
- **Certified copies:** Supported
""")

st.divider()
st.caption("SigGuard LK — RQ3 Hybrid Verification · MSc Research")