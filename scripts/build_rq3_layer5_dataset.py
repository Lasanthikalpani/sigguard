"""
RQ3 Layer 5: Build evaluation dataset for document amendment.

Creates two categories of test documents:
  A. legit_amendments — properly issued amendments (new QR, new hash)
  B. fake_amendments  — fraudulent (old QR + new content)

For each category, the script:
  1. Picks a raw document + signature
  2. Issues an original via the API (/issue-and-embed)
  3. Simulates a surname change
  4. For legit: issues a real amendment via /amendment/amend
     For fake:  just overlays new content (keeping old QR)

Output: data/rq3_layer5_eval/{legit_amendments,fake_amendments}/*.png
"""
import base64
import io
import json
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"
RAW_DOCS_DIR = Path("data/rq3_dataset/documents")
SIG_DIR = Path("data/rq3_dataset/signatures/sinhala")
OUT_DIR = Path("data/rq3_layer5_eval")

N_PER_CATEGORY = 50


# ============================================================
# Helpers
# ============================================================

def check_api():
    try:
        r = requests.get(f"{API}/api/v1/amendment/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def make_surname_change(original_img: Image.Image, new_surname: str) -> Image.Image:
    """Simulate a surname change by overlaying new text."""
    amended = original_img.copy()
    draw = ImageDraw.Draw(amended)
    w, h = amended.size
    draw.rectangle([50, int(h * 0.3), int(w * 0.6), int(h * 0.36)], fill="white")
    draw.text((60, int(h * 0.31)), f"Name: {new_surname}", fill="black")
    return amended


def img_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ============================================================
# Issue original via API
# ============================================================

def issue_original(doc_path: Path, sig_path: Path) -> dict:
    """POST to /issue-and-embed. Returns API response dict."""
    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (doc_path.name, doc_path.read_bytes(), "image/png"),
            "signature": (sig_path.name, sig_path.read_bytes(), "image/png"),
        },
        data={"issuer": "GovLK-Eval", "ai_confidence": "0.95"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"issue-and-embed failed: {r.text}")
    return r.json()


def issue_amendment(original_doc_id: str, amended_bytes: bytes, sig_path: Path) -> dict:
    """POST to /amendment/amend. Returns API response dict."""
    r = requests.post(
        f"{API}/api/v1/amendment/amend",
        files={
            "new_document": ("amended.png", amended_bytes, "image/png"),
            "new_signature": (sig_path.name, sig_path.read_bytes(), "image/png"),
        },
        data={
            "original_doc_id": original_doc_id,
            "amendment_reason": "surname_change",
            "issuer": "Registrar General's Office",
            "evidence_json": json.dumps({"marriage_cert": "MC-2026-XXX"}),
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"amendment/amend failed: {r.text}")
    return r.json()


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  Build RQ3 Layer 5 Evaluation Dataset")
    print("=" * 70)

    if not check_api():
        print(f"[ERROR] API not running at {API}")
        return

    # Clean output
    if OUT_DIR.exists():
        import shutil
        shutil.rmtree(OUT_DIR)
    (OUT_DIR / "legit_amendments").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fake_amendments").mkdir(parents=True, exist_ok=True)

    raw_docs = sorted(RAW_DOCS_DIR.rglob("*.png"))
    sig_files = sorted(SIG_DIR.glob("*.png"))

    if not raw_docs or not sig_files:
        print(f"[ERROR] Missing raw docs or signatures")
        return

    print(f"\n[INFO] Raw docs:    {len(raw_docs)}")
    print(f"[INFO] Signatures:  {len(sig_files)}")
    print(f"[INFO] Target:      {N_PER_CATEGORY} × 2 = {N_PER_CATEGORY * 2} amendments\n")

    # Cycle through raw docs + sigs
    legit_count = 0
    fake_count = 0
    errors = 0

    for i in range(N_PER_CATEGORY):
        doc_path = raw_docs[i % len(raw_docs)]
        sig_path = sig_files[i % len(sig_files)]

        # ---- Issue an original ----
        try:
            orig_result = issue_original(doc_path, sig_path)
        except Exception as e:
            print(f"  [{i+1:>3}] [ERROR] issue original: {e}")
            errors += 1
            continue

        original_doc_id = orig_result["document_id"]
        original_bytes = base64.b64decode(orig_result["stamped_document_base64"])
        original_img = Image.open(io.BytesIO(original_bytes))

        # ---- Simulate surname change ----
        amended_img = make_surname_change(original_img, f"PERERA{i:03d}")
        amended_bytes = img_to_bytes(amended_img)

        # ---- (A) Legitimate amendment: issue via API ----
        try:
            amend_result = issue_amendment(original_doc_id, amended_bytes, sig_path)
            legit_bytes = base64.b64decode(amend_result["stamped_document_base64"])
            legit_path = OUT_DIR / "legit_amendments" / f"{original_doc_id}-AMD.png"
            legit_path.write_bytes(legit_bytes)
            legit_count += 1
        except Exception as e:
            print(f"  [{i+1:>3}] [ERROR] legit amend: {e}")
            errors += 1
            # Continue — still try the fake one

        # ---- (B) Fake amendment: old QR + new content (no API call) ----
        fake_path = OUT_DIR / "fake_amendments" / f"{original_doc_id}-FAKE.png"
        fake_path.write_bytes(amended_bytes)
        fake_count += 1

        if (i + 1) % 10 == 0:
            print(f"  [{i+1:>3}/{N_PER_CATEGORY}] legit={legit_count} fake={fake_count}")

    # Summary
    print()
    print("=" * 70)
    print("  DATASET BUILT")
    print("=" * 70)
    print(f"  legit_amendments:  {legit_count}")
    print(f"  fake_amendments:   {fake_count}")
    if errors:
        print(f"  [WARN] Errors:     {errors}")
    print()
    print(f"Output: {OUT_DIR.absolute()}")
    print()
    print("Next: python scripts/rq3_layer5_evaluation.py")
    print()


if __name__ == "__main__":
    main()