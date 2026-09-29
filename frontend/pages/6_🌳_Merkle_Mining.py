"""RQ3 Page 6 — Merkle Tree & Block Mining (SigVerify Theory)."""
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.services.merkle_service import MerkleTree
from src.api.services.mining_service import MiningService

st.set_page_config(
    page_title="Merkle Mining — SigVerify",
    page_icon="🌳",
    layout="wide",
)

st.title("🌳 Merkle Tree & Block Mining")
st.markdown("""
**SigVerify Theory: 2000 documents per block, 99.95% storage reduction**
""")

st.divider()

# ============================================================
# SECTION 1: Merkle Tree Statistics
# ============================================================
st.subheader("📊 Merkle Tree Statistics")

n_docs = st.slider("Number of documents", 100, 5000, 2000, 100)

if st.button("🔄 Compute Merkle Tree", type="primary"):
    with st.spinner(f"Building Merkle Tree with {n_docs} documents..."):
        start = time.time()
        docs = [f"doc-{i}" for i in range(n_docs)]
        mt = MerkleTree(docs)
        stats = mt.get_stats()
        elapsed = time.time() - start

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Documents", f"{n_docs:,}")
    with col2:
        st.metric("Tree Levels", stats["levels"])
    with col3:
        st.metric("Storage Reduction", f"{stats['storage_reduction_pct']}%")
    with col4:
        st.metric("Build Time", f"{elapsed*1000:.1f} ms")

    st.success(f"✅ Merkle Root: `{stats['root'][:32]}...`")

    # Storage comparison
    st.markdown("### 📦 Storage Comparison")
    col1, col2 = st.columns(2)
    with col1:
        st.metric(
            "Traditional (linear)",
            f"{stats['traditional_size_bytes']:,} bytes",
        )
    with col2:
        st.metric(
            "Merkle Tree",
            f"{stats['root_size_bytes']} bytes",
        )

    # Verification speed
    st.markdown("### ⚡ Verification Speed")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Linear", f"{n_docs:,} steps")
    with col2:
        st.metric("Merkle", f"{stats['verification_steps']} steps")
    with col3:
        speedup = n_docs // max(stats["verification_steps"], 1)
        st.metric("Speedup", f"{speedup}x")

# ============================================================
# SECTION 2: Block Mining Simulation
# ============================================================
st.divider()
st.subheader("⛏️ Block Mining Simulation")

col1, col2 = st.columns(2)
with col1:
    batch_size = st.number_input("Batch size", 10, 5000, 2000, 10)
with col2:
    difficulty = st.number_input("PoW difficulty", 1, 5, 2)

if st.button("⛏️ Mine Block", type="primary"):
    path = Path("data/blockchain/ui_mining_chain.json")
    if path.exists():
        path.unlink()

    with st.spinner(f"Mining block with {batch_size} transactions..."):
        service = MiningService(
            batch_size=batch_size,
            difficulty=difficulty,
            chain_path=str(path),
        )

        start = time.time()
        for i in range(batch_size):
            service.add_document({"doc_id": f"BC-{i:06d}"})
        elapsed = time.time() - start

        block = service.chain[-1]

    st.success(f"✅ Block {block.index} mined in {elapsed*1000:.1f} ms")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Nonce", block.nonce)
    with col2:
        st.metric("Transactions", batch_size)
    with col3:
        st.metric("Time", f"{elapsed*1000:.1f} ms")

    st.json({
        "index": block.index,
        "merkle_root": block.merkle_root[:32] + "...",
        "block_hash": block.hash[:32] + "...",
        "previous_hash": block.previous_hash[:32] + "...",
        "nonce": block.nonce,
    })

st.divider()
st.caption("SigVerify — Merkle Tree & Mining · MSc Research · University of Sri Jayewardenepura")