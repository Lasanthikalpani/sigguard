"""
Build RQ3 evaluation dataset with proper ground truth.

Creates 7 categories from the base RQ3 dataset:
1. clean           — QR-embedded, untouched          (authentic)
2. tampered_content — QR-embedded, then content edited (tampered)
3. tampered_qr      — QR-embedded, then QR destroyed   (tampered)
4. tampered_qr_partial — QR-embedded, partial QR damage (tampered)
5. degraded_blur    — QR-embedded, then blurred        (authentic)
6. degraded_aging   — QR-embedded, then aged           (authentic)
7. degraded_lowdpi  — QR-embedded, then low-DPI        (authentic)

Output: data/rq3_eval/{category}/*.png
"""
import sys
import random
import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.crypto_service import CryptoService
from src.api.services.qr_service import QRService

random.seed(42)

# Source
SRC_DOCS = Path("data/rq3_dataset/documents")
SRC_SIGS = Path("data/rq3_dataset/signatures")

# Output
OUT_DIR = Path("data/rq3_eval")
CATEGORIES = [
    "clean",
    "tampered_content",
    "tampered_qr",
    "tampered_qr_partial",
    "degraded_blur",
    "degraded_aging",
    "degraded_lowdpi",
]

N_PER_CATEGORY = 100  # 100 docs per category → 700 total

_crypto = CryptoService()
_qr = QRService()


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def pick_source_docs(n):
    """Pick n clean documents spread across all 5 types."""
    all_docs = sorted(SRC_DOCS.rglob("*.png"))
    random.shuffle(all_docs)
    return all_docs[:n]


def pick_signature_for(doc_path):
    """Pick any signature (for QR embedding we just need a sig hash)."""
    script = random.choice(["sinhala", "tamil", "english"])
    sigs = sorted((SRC_SIGS / script).glob("*.png"))
    if not sigs:
        return None
    return random.choice(sigs)


def embed_qr_into(doc_bytes: bytes, sig_bytes: bytes, doc_id: str, issuer: str = "GovLK-Eval"):
    """Reproduce issue-and-embed logic locally (no API call)."""
    doc_hash = _crypto.compute_content_hash_with_mask(doc_bytes)
    sig_hash = _crypto.compute_signature_hash(sig_bytes)

    record = _crypto.build_integrity_record(
        document_id=doc_id,
        document_hash=doc_hash,
        signature_hash=sig_hash,
        ai_confidence=0.95,
        metadata={"issuer": issuer},
    )
    qr_bytes = _qr.encode_record(record)
    stamped = _qr.embed_in_document(doc_bytes, qr_bytes, position="bottom-right")
    return stamped, record


def tamper_content(img: Image.Image) -> Image.Image:
    """Overwrite a text region in the document body."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    w, h = tampered.size
    # Pick a region in the upper-middle (where names/IDs are)
    draw.rectangle([50, int(h * 0.3), int(w * 0.5), int(h * 0.35)], fill="white")
    draw.text((60, int(h * 0.31)), "TAMPERED CONTENT - FORGED", fill="red")
    return tampered


def tamper_qr_destroyed(img: Image.Image) -> Image.Image:
    """Cover the entire QR region (bottom-right) with black."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    w, h = tampered.size
    # Match QRService.embed_in_document geometry
    qr_size = max(400, int(min(w, h) * 0.35))
    margin = 20
    x1 = w - qr_size - margin
    y1 = h - qr_size - margin
    draw.rectangle([x1, y1, w, h], fill="black")
    return tampered


def tamper_qr_partial(img: Image.Image) -> Image.Image:
    """Partially damage the QR (white patch over a quadrant)."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    w, h = tampered.size
    qr_size = max(400, int(min(w, h) * 0.35))
    margin = 20
    x1 = w - qr_size - margin
    y1 = h - qr_size - margin
    # Cover ~35% of QR (a corner)
    cx = x1 + int(qr_size * 0.35)
    cy = y1 + int(qr_size * 0.35)
    draw.rectangle([x1, y1, cx, cy], fill="white")
    return tampered


def degrade_blur(img: Image.Image) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=1.0))


def degrade_aging(img: Image.Image) -> Image.Image:
    w, h = img.size
    yellow = Image.new("RGB", (w, h), color=(255, 245, 220))
    return Image.blend(img, yellow, alpha=0.3)


def degrade_lowdpi(img: Image.Image) -> Image.Image:
    w, h = img.size
    low = img.resize((int(w * 0.5), int(h * 0.5)), Image.LANCZOS)
    return low.resize((w, h), Image.LANCZOS)


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    print("=" * 70)
    print("  Build RQ3 Evaluation Dataset")
    print("=" * 70)

    # Clean output dir
    if OUT_DIR.exists():
        print(f"\n[INFO] Removing existing {OUT_DIR}")
        shutil.rmtree(OUT_DIR)

    for cat in CATEGORIES:
        (OUT_DIR / cat).mkdir(parents=True, exist_ok=True)

    # Pick source docs
    src_docs = pick_source_docs(N_PER_CATEGORY)
    if not src_docs:
        print(f"[ERROR] No source documents in {SRC_DOCS}")
        return

    print(f"\n[INFO] Picked {len(src_docs)} source documents")
    print(f"[INFO] Target: {N_PER_CATEGORY} per category × {len(CATEGORIES)} = {N_PER_CATEGORY * len(CATEGORIES)} files")
    print()

    counts = {c: 0 for c in CATEGORIES}
    qr_fail = 0

    for i, doc_path in enumerate(src_docs, start=1):
        doc_bytes = doc_path.read_bytes()
        sig_path = pick_signature_for(doc_path)
        if sig_path is None:
            continue
        sig_bytes = sig_path.read_bytes()

        doc_id = f"RQ3EVAL-{i:04d}"

        # First: embed QR (creates the "clean" stamped document)
        try:
            stamped_bytes, _ = embed_qr_into(doc_bytes, sig_bytes, doc_id)
        except Exception as e:
            qr_fail += 1
            continue

        stamped_img = Image.open(__import__("io").BytesIO(stamped_bytes)).convert("RGB")

        # 1. clean
        stamped_img.save(OUT_DIR / "clean" / f"{doc_id}_clean.png", format="PNG")
        counts["clean"] += 1

        # 2. tampered_content
        t = tamper_content(stamped_img)
        t.save(OUT_DIR / "tampered_content" / f"{doc_id}_content.png", format="PNG")
        counts["tampered_content"] += 1

        # 3. tampered_qr
        t = tamper_qr_destroyed(stamped_img)
        t.save(OUT_DIR / "tampered_qr" / f"{doc_id}_qrdestroyed.png", format="PNG")
        counts["tampered_qr"] += 1

        # 4. tampered_qr_partial
        t = tamper_qr_partial(stamped_img)
        t.save(OUT_DIR / "tampered_qr_partial" / f"{doc_id}_qrpartial.png", format="PNG")
        counts["tampered_qr_partial"] += 1

        # 5. degraded_blur
        t = degrade_blur(stamped_img)
        t.save(OUT_DIR / "degraded_blur" / f"{doc_id}_blur.png", format="PNG")
        counts["degraded_blur"] += 1

        # 6. degraded_aging
        t = degrade_aging(stamped_img)
        t.save(OUT_DIR / "degraded_aging" / f"{doc_id}_aging.png", format="PNG")
        counts["degraded_aging"] += 1

        # 7. degraded_lowdpi
        t = degrade_lowdpi(stamped_img)
        t.save(OUT_DIR / "degraded_lowdpi" / f"{doc_id}_lowdpi.png", format="PNG")
        counts["degraded_lowdpi"] += 1

        if i % 10 == 0:
            print(f"  [{i:>3}/{len(src_docs)}] processed")

    # Summary
    print()
    print("=" * 70)
    print("  DATASET BUILT")
    print("=" * 70)
    for cat in CATEGORIES:
        print(f"  {cat:<22} {counts[cat]:>4} files")
    print(f"  {'TOTAL':<22} {sum(counts.values()):>4} files")
    if qr_fail:
        print(f"\n  [WARN] QR embedding failed for {qr_fail} documents")
    print()
    print(f"Output: {OUT_DIR.absolute()}")
    print()
    print("Next: python scripts/rq3_tamper_evaluation.py")
    print()


if __name__ == "__main__":
    main()