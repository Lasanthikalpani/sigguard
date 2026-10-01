"""
RQ3 Layer 5: API-level test for document amendment.

Flow:
  1. Issue a fresh original via /api/v1/hybrid/issue-and-embed
     (this also registers the original in the API's ledger)
  2. Simulate a surname change (new content image)
  3. POST /api/v1/amendment/amend          → get amended doc
  4. POST /api/v1/amendment/verify         → verify amended doc
  5. FAKE amendment test (old QR + new content) → must be TAMPERED
  6. GET  /api/v1/amendment/lineage/{id}   → show lineage

Requires:
  - SigGuard API running on http://localhost:8000
  - data/rq3_dataset/documents/*.png (raw, no QR)
  - data/rq3_dataset/signatures/sinhala/*.png
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
TEST_DIR = Path("test_data/layer5")
TEST_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# Helpers
# ============================================================

def check_api():
    try:
        r = requests.get(f"{API}/api/v1/amendment/health", timeout=3)
        if r.status_code == 200:
            print(f"[OK] API healthy: {r.json()['status']}")
            return True
    except Exception as e:
        print(f"[ERROR] API not running: {e}")
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
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  RQ3 Layer 5 — API Test (Document Amendment)")
    print("=" * 70)

    if not check_api():
        return

    # ---- Step 1: Issue a fresh original via API ----
    print(f"\n[1] POST {API}/api/v1/hybrid/issue-and-embed ...")

    raw_docs = sorted(RAW_DOCS_DIR.rglob("*.png"))
    sig_files = sorted(SIG_DIR.glob("*.png"))
    if not raw_docs or not sig_files:
        print(f"[ERROR] Missing raw docs or signatures")
        print(f"  raw docs:  {len(raw_docs)}")
        print(f"  sig files: {len(sig_files)}")
        return

    raw_doc_path = raw_docs[0]
    sig_path = sig_files[0]
    print(f"    raw doc:  {raw_doc_path.name}")
    print(f"    sig:      {sig_path.name}")

    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (raw_doc_path.name, raw_doc_path.read_bytes(), "image/png"),
            "signature": (sig_path.name, sig_path.read_bytes(), "image/png"),
        },
        data={"issuer": "GovLK-Eval", "ai_confidence": "0.95"},
        timeout=60,
    )
    print(f"    HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"    [ERROR] {r.text}")
        return

    issue_result = r.json()
    original_doc_id = issue_result["document_id"]
    original_bytes = base64.b64decode(issue_result["stamped_document_base64"])

    original_path = TEST_DIR / "original_stamped.png"
    original_path.write_bytes(original_bytes)

    print(f"    [OK] Original issued:")
    print(f"         doc_id:      {original_doc_id}")
    print(f"         block_index: {issue_result['blockchain']['block_index']}")
    print(f"         saved:       {original_path}")

    # ---- Step 2: Simulate surname change ----
    print(f"\n[2] Simulating surname change (Chandrasekara → Perera) ...")
    original_img = Image.open(io.BytesIO(original_bytes))
    amended_img = make_surname_change(original_img, "PERERA")
    amended_bytes = img_to_bytes(amended_img)

    amended_new_path = TEST_DIR / "amended_new_content.png"
    amended_new_path.write_bytes(amended_bytes)
    print(f"    [OK] New content saved: {amended_new_path}")

    # ---- Step 3: Issue amendment via API ----
    print(f"\n[3] POST {API}/api/v1/amendment/amend ...")
    r = requests.post(
        f"{API}/api/v1/amendment/amend",
        files={
            "new_document": ("amended.png", amended_bytes, "image/png"),
            "new_signature": ("sig.png", sig_path.read_bytes(), "image/png"),
        },
        data={
            "original_doc_id": original_doc_id,
            "amendment_reason": "surname_change",
            "issuer": "Registrar General's Office",
            "evidence_json": json.dumps({"marriage_cert": "MC-2026-001"}),
        },
        timeout=60,
    )
    print(f"    HTTP {r.status_code}")
    if r.status_code != 200:
        print(f"    [ERROR] {r.text}")
        return

    result = r.json()
    amended_doc_id = result["amended_doc_id"]
    stamped_bytes = base64.b64decode(result["stamped_document_base64"])
    stamped_path = TEST_DIR / "amended_stamped.png"
    stamped_path.write_bytes(stamped_bytes)

    print(f"    [OK] Amendment issued:")
    print(f"         amended_doc_id: {amended_doc_id}")
    print(f"         reason:         {result['amendment_reason_display']}")
    print(f"         block_index:    {result['blockchain']['block_index']}")
    print(f"         saved:          {stamped_path}")

    # ---- Step 4: Verify amended document ----
    print(f"\n[4] POST {API}/api/v1/amendment/verify (amended doc) ...")
    r = requests.post(
        f"{API}/api/v1/amendment/verify",
        files={"document": ("amended_stamped.png", stamped_bytes, "image/png")},
        timeout=60,
    )
    print(f"    HTTP {r.status_code}")
    if r.status_code == 200:
        v = r.json()
        print(f"    status:       {v['status']}")
        print(f"    document_id:  {v.get('document_id')}")
        if v.get("blockchain"):
            bc = v["blockchain"]
            print(f"    is_amendment: {bc['is_amendment']}")
            print(f"    original:     {bc.get('original_doc_id')}")
            print(f"    reason:       {bc.get('amendment_reason')}")
        expected = "AMENDED_AUTHENTIC"
        ok = v["status"] == expected
        print(f"    expected:     {expected}   {'✅' if ok else '❌'}")

    # ---- Step 5: FAKE amendment test ----
    print(f"\n[5] FAKE amendment test (old QR + new content) ...")
    fake_img = make_surname_change(original_img, "FRAUDSTER")
    fake_bytes = img_to_bytes(fake_img)
    fake_path = TEST_DIR / "fake_amendment.png"
    fake_path.write_bytes(fake_bytes)

    r = requests.post(
        f"{API}/api/v1/amendment/verify",
        files={"document": ("fake.png", fake_bytes, "image/png")},
        timeout=60,
    )
    print(f"    HTTP {r.status_code}")
    if r.status_code == 200:
        v = r.json()
        print(f"    status:   {v['status']}")
        expected = "TAMPERED"
        ok = v["status"] == expected
        print(f"    expected: {expected}   {'✅' if ok else '❌'}")

    # ---- Step 6: Lineage query ----
    print(f"\n[6] GET {API}/api/v1/amendment/lineage/{amended_doc_id} ...")
    r = requests.get(f"{API}/api/v1/amendment/lineage/{amended_doc_id}", timeout=10)
    print(f"    HTTP {r.status_code}")
    if r.status_code == 200:
        lin = r.json()
        print(f"    lineage_length: {lin['lineage_length']}")
        for b in lin["lineage"]:
            marker = " [AMENDMENT]" if b.get("metadata", {}).get("is_amendment") else " [ORIGINAL]"
            print(f"      - {b['doc_id']}{marker}")

    # ---- Summary ----
    print()
    print("=" * 70)
    print("  TEST COMPLETE")
    print("=" * 70)
    print(f"  Original doc_id:  {original_doc_id}")
    print(f"  Amended doc_id:   {amended_doc_id}")
    print(f"  Artifacts:        {TEST_DIR.absolute()}")
    print()


if __name__ == "__main__":
    main()