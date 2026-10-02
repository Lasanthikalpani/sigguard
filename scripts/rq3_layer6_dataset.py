"""
RQ3 Layer 6: Build evaluation dataset for copy vs original.

Creates 4 categories of test documents:
  1. originals        — properly issued original docs
  2. certified_copies — registry-issued certified copies (new QR, new timestamp)
  3. photocopies      — exact copies of originals (same QR, same timestamp)
  4. forged_copies    — old QR + modified content (fraud)

For each category, the script:
  1. Picks a raw document + signature
  2. Issues an original via /api/v1/hybrid/issue-and-embed
  3. Creates the variant
  4. Saves to data/rq3_layer6_eval/{category}/

Output: data/rq3_layer6_eval/{originals,certified_copies,photocopies,forged_copies}/
"""
import base64
import io
import shutil
import sys
from pathlib import Path

import requests
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"
RAW_DOCS_DIR = Path("data/rq3_dataset/documents")
SIG_DIR = Path("data/rq3_dataset/signatures/sinhala")
OUT_DIR = Path("data/rq3_layer6_eval")

N_PER_CATEGORY = 25


# ============================================================
# Helpers
# ============================================================

def check_api():
    try:
        r = requests.get(f"{API}/api/v1/copy/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def issue_original(doc_path: Path, sig_path: Path) -> dict:
    """POST to /issue-and-embed. Returns API response dict."""
    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (doc_path.name, doc_path.read_bytes(), "image/png"),
            "signature": (sig_path.name, sig_path.read_bytes(), "image/png"),
        },
        data={"issuer": "GovLK-Layer6", "ai_confidence": "0.95"},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"issue-and-embed failed: {r.text}")
    return r.json()


def issue_certified_copy(original_doc_id: str) -> dict:
    """POST to /api/v1/copy/issue-certified. Returns API response dict."""
    r = requests.post(
        f"{API}/api/v1/copy/issue-certified",
        data={
            "original_doc_id": original_doc_id,
            "certifier": "Registrar General's Office",
            "reason": "citizen_request",
        },
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"issue-certified failed: {r.text}")
    return r.json()


def make_photocopy(original_bytes: bytes) -> bytes:
    """
    Simulate a photocopy: keep the same QR, same content, but re-encode.
    (A real photocopy is a scan of the original.)
    """
    img = Image.open(io.BytesIO(original_bytes))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def make_forged_copy(original_bytes: bytes) -> bytes:
    """
    Simulate a forged copy: keep the original QR, but change the content.
    """
    img = Image.open(io.BytesIO(original_bytes)).convert("RGB")
    draw = ImageDraw.Draw(img)
    w, h = img.size
    # Overlay forged text in the upper-middle region
    draw.rectangle([50, int(h * 0.3), int(w * 0.6), int(h * 0.36)], fill="white")
    draw.text((60, int(h * 0.31)), "Name: FRAUDSTER FORGED", fill="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  Build RQ3 Layer 6 Evaluation Dataset")
    print("=" * 70)

    if not check_api():
        print(f"[ERROR] API not running at {API}")
        return

    # Clean output
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    for cat in ["originals", "certified_copies", "photocopies", "forged_copies"]:
        (OUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    raw_docs = sorted(RAW_DOCS_DIR.rglob("*.png"))
    sig_files = sorted(SIG_DIR.glob("*.png"))

    if not raw_docs or not sig_files:
        print(f"[ERROR] Missing raw docs or signatures")
        return

    print(f"\n[INFO] Raw docs:    {len(raw_docs)}")
    print(f"[INFO] Signatures:  {len(sig_files)}")
    print(f"[INFO] Target:      {N_PER_CATEGORY} × 4 = {N_PER_CATEGORY * 4} docs\n")

    counts = {
        "originals": 0,
        "certified_copies": 0,
        "photocopies": 0,
        "forged_copies": 0,
    }
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

        # (1) Save original
        (OUT_DIR / "originals" / f"{original_doc_id}.png").write_bytes(original_bytes)
        counts["originals"] += 1

        # (2) Issue certified copy
                # (2) Issue certified copy
        # IMPORTANT: Use the RAW document (no QR) as content, not the stamped original.
        # Otherwise the original QR and the new QR overlap, causing decode failures.
        try:
            cc_result = issue_certified_copy(original_doc_id)
            cc_doc_id = cc_result["certified_copy_id"]
            cc_qr_bytes = base64.b64decode(cc_result["new_qr_base64"])

            # Build fresh certified-copy image from the RAW document content
            from src.api.services.qr_service import QRService
            qr_svc = QRService()
            raw_bytes = doc_path.read_bytes()
            cc_stamped = qr_svc.embed_in_document(
                raw_bytes, cc_qr_bytes, position="bottom-right"
            )
            (OUT_DIR / "certified_copies" / f"{cc_doc_id}.png").write_bytes(cc_stamped)
            counts["certified_copies"] += 1
        except Exception as e:
            print(f"  [{i+1:>3}] [ERROR] certified copy: {e}")
            errors += 1

        # (3) Photocopy (same bytes, re-saved)
        photo_bytes = make_photocopy(original_bytes)
        (OUT_DIR / "photocopies" / f"{original_doc_id}-PHOTO.png").write_bytes(photo_bytes)
        counts["photocopies"] += 1

        # (4) Forged copy (original QR + changed content)
        forged_bytes = make_forged_copy(original_bytes)
        (OUT_DIR / "forged_copies" / f"{original_doc_id}-FORGED.png").write_bytes(forged_bytes)
        counts["forged_copies"] += 1

        if (i + 1) % 5 == 0:
            print(f"  [{i+1:>3}/{N_PER_CATEGORY}] {counts}")

    # Summary
    print()
    print("=" * 70)
    print("  DATASET BUILT")
    print("=" * 70)
    for cat, n in counts.items():
        print(f"  {cat:<20} {n}")
    if errors:
        print(f"  [WARN] Errors:        {errors}")
    print()
    print(f"Output: {OUT_DIR.absolute()}")
    print()
    print("Next: python scripts/rq3_layer6_evaluation.py")
    print()


if __name__ == "__main__":
    main()