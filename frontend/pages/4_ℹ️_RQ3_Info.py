"""
RQ3 Frontend — Page 4: Engine Info & Health
"""
import requests
import streamlit as st

API_URL = "http://localhost:8000"
HYBRID_API = f"{API_URL}/api/v1/hybrid"

st.set_page_config(page_title="RQ3 Info — SigGuard LK", page_icon="ℹ️", layout="wide")

st.title("ℹ️ RQ3 Engine Information")

st.markdown("""
**RQ3 — Explainable AI for Signature Forgery Detection in Sri Lankan Government Documents
Using Siamese CNN + Hybrid QR Cryptographic Verification**
""")

st.divider()

# Health
st.subheader("🏥 Service Health")
try:
    health = requests.get(f"{HYBRID_API}/health", timeout=3).json()
    st.json(health)
except Exception as e:
    st.error(f"❌ API unreachable: {e}")

st.divider()

# Info
st.subheader("⚙️ Engine Configuration")
try:
    info = requests.get(f"{HYBRID_API}/info", timeout=3).json()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("AI Weight", info["fusion_weights"]["ai"])
    with col2:
        st.metric("Crypto Weight", info["fusion_weights"]["crypto"])
    with col3:
        st.metric("AI Threshold", info["thresholds"]["ai"])
    with col4:
        st.metric("Crypto Threshold", info["thresholds"]["crypto"])
    
    st.json(info)
except Exception as e:
    st.error(f"❌ Could not fetch info: {e}")

st.divider()

# Architecture
st.subheader("🏗️ Architecture Overview")
st.markdown("")