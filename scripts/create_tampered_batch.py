"""
Create tampered documents for batch verify testing.

Takes the QR-embedded documents and creates tampered variants:
- qr_destroyed: QR code covered with black rectangle
- content_changed: Part of document content modified
- qr_partial: Partial QR damage

Saves to: test_data/batch_tampered/
"""
import io
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

INPUT_DIR = Path("test_data/batch_with_qr")
OUTPUT_DIR = Path("test_data/batch_tampered")


def tamper_qr_destroyed(img: Image.Image) -> Image.Image:
    """Cover the entire QR area with black."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    w, h = tampered.size
    # Cover bottom-right corner (QR area)
    draw.rectangle([int(w * 0.55), int(h * 0.55), w, h], fill="black")
    return tampered


def tamper_content_change(img: Image.Image) -> Image.Image:
    """Modify a text field (content tampering)."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    # Cover a region and add new text
    draw.rectangle([50, 200, 400, 240], fill="white")
    draw.text((60, 210), "TAMPERED CONTENT - FORGED", fill="red")
    return tampered


def tamper_qr_partial(img: Image.Image) -> Image.Image:
    """Partially damage the QR (some modules still visible)."""
    tampered = img.copy()
    draw = ImageDraw.Draw(tampered)
    w, h = tampered.size
    # Cover part of QR region
    draw.rectangle([int(w * 0.7), int(h * 0.7), int(w * 0.9), int(h * 0.9)], fill="white")
    return tampered


def main():
    print("=" * 70)
    print("  Create Tampered Documents for Batch Verify")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Original QR-embedded documents
    qr_docs = sorted(INPUT_DIR.glob("*_with_qr.png"))
    if not qr_docs:
        print(f"[ERROR] No QR documents found in {INPUT_DIR}")
        print("Run: python scripts/batch_issue_documents.py first")
        return

    print(f"\n[INFO] Found {len(qr_docs)} QR-embedded documents")
    print(f"[INFO] Creating tampered variants...\n")

    tamper_functions = [
        ("qr_destroyed", tamper_qr_destroyed),
        ("content_changed", tamper_content_change),
        ("qr_partial", tamper_qr_partial),
    ]

    created = []

    # Create tampered versions of first 3 documents
    for i, (doc_path, (tamper_name, tamper_fn)) in enumerate(
        zip(qr_docs[:3], tamper_functions), start=1
    ):
        img = Image.open(doc_path)
        tampered = tamper_fn(img)

        output_name = f"tampered_{i:02d}_{tamper_name}.png"
        output_path = OUTPUT_DIR / output_name
        tampered.save(output_path, format="PNG")

        created.append({
            "name": output_name,
            "source": doc_path.name,
            "tamper_type": tamper_name,
            "size": output_path.stat().st_size,
        })

        print(f"   [OK] {output_name}")
        print(f"        source:      {doc_path.name}")
        print(f"        tamper type: {tamper_name}")
        print(f"        size:        {output_path.stat().st_size:,} bytes")
        print()

    # Also copy corresponding signatures (for batch verify pairing)
    for i in range(1, 4):
        sig_name = f"{i:02d}_sig_sig_0{i}_"
        sig_files = list(INPUT_DIR.glob(f"{i:02d}_sig_*.png"))
        if sig_files:
            src = sig_files[0]
            dst = OUTPUT_DIR / f"{i:02d}_{src.name}"
            shutil.copy(src, dst)
            print(f"   [OK] {dst.name}  (signature, copied)")

    # Summary
    print()
    print("=" * 70)
    print(f"  COMPLETE — {len(created)} tampered documents created")
    print("=" * 70)
    print()
    print(f"Output folder: {OUTPUT_DIR.absolute()}")
    print()
    print("Tampered documents:")
    for c in created:
        print(f"   {c['name']} ({c['tamper_type']})")
    print()
    print("Next steps:")
    print("  1. Go to: http://localhost:8501")
    print("  2. Navigate to: Batch Verify")
    print("  3. Mix authentic + tampered documents in one batch")
    print("  4. Expected: Authentic count + Tampered count both non-zero")
    print()


if __name__ == "__main__":
    main()