"""SigGuard Streamlit Frontend."""
import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="SigGuard",
    page_icon="shield",
    layout="wide",
)

st.title("SigGuard")
st.subheader("AI-Powered Signature Forgery Detection")

with st.sidebar:
    st.header("About")
    st.write("Siamese CNN based signature forgery detection")
    st.write("Model v2:")
    st.write("- Accuracy: 99.50%")
    st.write("- F1: 99.50%")
    st.write("- AUC-ROC: 99.98%")

    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            st.success("API Online")
    except Exception:
        st.error("API Offline")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Reference Signature")
    reference = st.file_uploader(
        "Upload genuine signature",
        type=["png", "jpg", "jpeg"],
        key="reference",
    )
    if reference:
        st.image(reference, use_container_width=True)

with col2:
    st.subheader("Test Signature")
    test = st.file_uploader(
        "Upload signature to verify",
        type=["png", "jpg", "jpeg"],
        key="test",
    )
    if test:
        st.image(test, use_container_width=True)

st.markdown("---")

if st.button("Verify Signature", type="primary", use_container_width=True):
    if not reference or not test:
        st.warning("Please upload both signatures")
    else:
        with st.spinner("Verifying..."):
            try:
                files = {
                    "reference": (reference.name, reference.getvalue(), "image/png"),
                    "test": (test.name, test.getvalue(), "image/png"),
                }
                response = requests.post(f"{API_URL}/verify", files=files)

                if response.status_code == 200:
                    result = response.json()

                    st.markdown("---")
                    st.header("Verification Result")

                    verdict = result["verdict"]
                    confidence = result["confidence"]
                    distance = result["distance"]
                    inference_time = result["inference_time_ms"]

                    if verdict == "genuine":
                        st.success("GENUINE")
                    else:
                        st.error("FORGED")

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Confidence", f"{confidence:.2%}")
                    col2.metric("Distance", f"{distance:.4f}")
                    col3.metric("Time", f"{inference_time:.0f} ms")

                    st.progress(confidence)
                else:
                    st.error(f"API Error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

st.caption("SigGuard v2 | MSc Research")
