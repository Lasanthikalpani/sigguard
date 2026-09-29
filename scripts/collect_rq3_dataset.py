"""
RQ3 Dataset Collection (Only RQ3-relevant data)

RQ3 Layers:
1. Crypto + QR  → needs documents (PNG/JPEG)
2. Blockchain   → needs metadata records
3. Hybrid Verify → needs documents + signatures + references

This script generates:
- 1,000 synthetic Sri Lankan government documents
- 1,000 signature regions (cropped)
- 1,000 reference signatures
- 3,000 degraded documents (blur, aging, low-DPI)
- 500 tampered documents
- 100,000 blockchain records
- 10,000 certified copies

No public signature datasets (those are for RQ1).
"""
import hashlib
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.blockchain_service import BlockchainLedger

random.seed(42)

# Output directories
DATA_DIR = Path("data/rq3_dataset")
DOCS_DIR = DATA_DIR / "documents"
SIGS_DIR = DATA_DIR / "signatures"
REFS_DIR = DATA_DIR / "references"
DEG_DIR = DATA_DIR / "degraded"
TAMPERED_DIR = DATA_DIR / "tampered"
BLOCKCHAIN_PATH = DATA_DIR / "blockchain" / "ledger_100k.json"

# Document types
DOCUMENT_TYPES = [
    ("land_deed", "Land Deed", 1000, 700),
    ("birth_cert", "Birth Certificate", 1000, 750),
    ("id_card", "National Identity Card", 850, 550),
    ("degree", "Degree Certificate", 1100, 800),
    ("vehicle_reg", "Vehicle Registration", 900, 600),
]

# Signature scripts (for RQ3's cross-script objective)
SIGNATURE_SCRIPTS = ["sinhala", "tamil", "english"]


def get_font(size):
    for font_name in ["arial.ttf", "calibri.ttf", "times.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


# ============================================================
# 1. SYNTHETIC DOCUMENTS
# ============================================================

def create_document(doc_type, title, width, height, doc_id):
    """Create a synthetic Sri Lankan government document."""
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)

    header_font = get_font(28)
    sub_font = get_font(16)
    body_font = get_font(14)
    small_font = get_font(12)

    # Border
    draw.rectangle([10, 10, width - 10, height - 10], outline="darkblue", width=3)
    draw.rectangle([15, 15, width - 15, height - 15], outline="gold", width=1)

    # Emblem
    draw.ellipse([40, 40, 100, 100], outline="darkblue", width=2)
    draw.ellipse([50, 50, 90, 90], fill="gold", outline="darkblue", width=1)
    draw.text((70, 75), "LK", font=get_font(20), fill="darkblue", anchor="mm")

    # Header
    draw.text(
        (width // 2, 60),
        "DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA",
        font=sub_font, fill="darkblue", anchor="mm",
    )
    draw.text(
        (width // 2, 100),
        title.upper(),
        font=header_font, fill="darkblue", anchor="mm",
    )
    draw.line([(30, 130), (width - 30, 130)], fill="darkblue", width=2)

    # Document ID
    draw.text((40, 150), f"Document ID: {doc_id}", font=body_font, fill="black")
    draw.text((40, 175), f"Issued: 2026-09-29", font=body_font, fill="black")
    draw.text((40, 200), f"Serial No: {random.randint(100000, 999999)}", font=body_font, fill="black")

    # Body fields
    y = 250
    for label in ["Name:", "NIC No:", "Address:", "District:"]:
        draw.text((40, y), label, font=body_font, fill="gray")
        draw.text((200, y), f"Sample_{random.randint(1000, 9999)}", font=body_font, fill="black")
        y += 30

    # Legal text
    y += 20
    for line in [
        "This document is issued under the authority of the Government of Sri Lanka.",
        "Any alteration, forgery, or unauthorized reproduction is a punishable offense.",
        "This document is invalid without the official seal and authorized signature.",
    ]:
        draw.text((40, y), line, font=small_font, fill="darkgray")
        y += 18

    # QR reserved area (bottom-right)
    qr_size = 400
    margin = 20
    qr_x = width - qr_size - margin
    qr_y = height - qr_size - margin
    draw.rectangle(
        [qr_x - 5, qr_y - 5, width - margin + 5, height - margin + 5],
        outline="gray", width=1,
    )
    draw.text(
        (qr_x + qr_size // 2, qr_y - 15),
        "QR Integrity Code (Reserved)",
        font=small_font, fill="gray", anchor="mm",
    )

    # Official seal (top-right)
    seal_x, seal_y = width - 120, 180
    draw.ellipse([seal_x - 60, seal_y - 60, seal_x + 60, seal_y + 60], outline="darkred", width=3)
    draw.text((seal_x, seal_y - 15), "OFFICIAL", font=small_font, fill="darkred", anchor="mm")
    draw.text((seal_x, seal_y + 5), "SEAL", font=small_font, fill="darkred", anchor="mm")

    # Signature area (bottom-left)
    sig_y = height - 100
    draw.line([(60, sig_y), (300, sig_y)], fill="black", width=1)
    draw.text((60, sig_y + 5), "Authorized Signature", font=small_font, fill="gray")

    return img


def generate_documents(num_per_type=200):
    """Generate 1,000 synthetic documents."""
    total = 0
    for doc_type, title, w, h in DOCUMENT_TYPES:
        for i in range(num_per_type):
            doc_id = f"LK-{doc_type.upper()}-{i:04d}"
            img = create_document(doc_type, title, w, h, doc_id)
            path = DOCS_DIR / doc_type / f"{doc_id}.png"
            path.parent.mkdir(parents=True, exist_ok=True)
            img.save(path, format="PNG")
            total += 1
    return total


# ============================================================
# 2. SIGNATURE REGIONS (cropped)
# ============================================================

def create_signature_region(script, signer_id, variation="genuine"):
    """Create a signature region image (400x200)."""
    img = Image.new("RGB", (400, 200), color="white")
    draw = ImageDraw.Draw(img)

    params = {
        "genuine":   {"jitter": 3,  "stroke": 3, "strokes": 8},
        "skilled":   {"jitter": 6,  "stroke": 3, "strokes": 8},
        "unskilled": {"jitter": 15, "stroke": 4, "strokes": 10},
    }[variation]

    random.seed(signer_id * 100 + hash(script) % 1000 + hash(variation) % 100)

    base_x, base_y = 50, 100
    current_x = base_x

    for i in range(params["strokes"]):
        points = []
        for j in range(4):
            x = current_x + j * random.randint(30, 60) + random.randint(-params["jitter"], params["jitter"])
            y = base_y + random.randint(-40, 40) + random.randint(-params["jitter"], params["jitter"])
            points.append((x, y))

        for k in range(len(points) - 1):
            x1, y1 = points[k]
            x2, y2 = points[k + 1]
            for t in range(20):
                t_val = t / 20.0
                x = int(x1 + (x2 - x1) * t_val + random.randint(-1, 1))
                y = int(y1 + (y2 - y1) * t_val + random.randint(-1, 1))
                draw.ellipse(
                    [x - params["stroke"], y - params["stroke"],
                     x + params["stroke"], y + params["stroke"]],
                    fill="black",
                )

        current_x = points[-1][0] + random.randint(5, 20)
        if i % 3 == 2:
            current_x = base_x + random.randint(0, 30)

    draw.line(
        [(base_x, base_y + 60), (base_x + random.randint(200, 300), base_y + 60)],
        fill="black", width=2,
    )
    return img


def generate_signatures(script, num_signers=100):
    """
    For each RQ3 document, generate:
    - 1 signature region (for the document)
    - 1 reference signature (for AI comparison)
    
    100 signers × 1 doc each × 3 scripts = 300 documents
    """
    total = 0
    for signer_id in range(1, num_signers + 1):
        # Signature region (test signature)
        sig_img = create_signature_region(script, signer_id, "genuine")
        sig_path = SIGS_DIR / script / f"signer_{signer_id:03d}_sig.png"
        sig_path.parent.mkdir(parents=True, exist_ok=True)
        sig_img.save(sig_path, format="PNG")

        # Reference signature (same as test — genuine)
        ref_img = create_signature_region(script, signer_id, "genuine")
        ref_path = REFS_DIR / script / f"signer_{signer_id:03d}_ref.png"
        ref_path.parent.mkdir(parents=True, exist_ok=True)
        ref_img.save(ref_path, format="PNG")

        total += 2

    return total


# ============================================================
# 3. DEGRADED DOCUMENTS
# ============================================================

def apply_degradations(num_docs=1000):
    """
    Apply 3 degradation types to N documents:
    - Blur (σ=1.0)
    - Aging (yellow tint)
    - Low DPI (downscale + upscale)
    """
    # Ensure sub-folders exist (defensive)
    for sub in ["blur", "aging", "low_dpi"]:
        (DEG_DIR / sub).mkdir(parents=True, exist_ok=True)

    total = 0
    doc_paths = list(DOCS_DIR.rglob("*.png"))[:num_docs]

    for doc_path in doc_paths:
        original = Image.open(doc_path).convert("RGB")

        # Blur
        blurred = original.filter(ImageFilter.GaussianBlur(radius=1.0))
        blurred.save(DEG_DIR / "blur" / f"{doc_path.stem}_blur.png", format="PNG")
        total += 1

        # Aging (yellow tint)
        w, h = original.size
        yellow = Image.new("RGB", (w, h), color=(255, 245, 220))
        aged = Image.blend(original, yellow, alpha=0.3)
        aged.save(DEG_DIR / "aging" / f"{doc_path.stem}_aged.png", format="PNG")
        total += 1

        # Low DPI
        low = original.resize((int(w * 0.5), int(h * 0.5)), Image.LANCZOS)
        low = low.resize((w, h), Image.LANCZOS)
        low.save(DEG_DIR / "low_dpi" / f"{doc_path.stem}_lowdpi.png", format="PNG")
        total += 1

    return total


# ============================================================
# 4. TAMPERED DOCUMENTS
# ============================================================

def generate_tampered(num_docs=500):
    """Create tampered variants of documents."""
    total = 0
    doc_paths = list(DOCS_DIR.rglob("*.png"))[:num_docs]

    for doc_path in doc_paths:
        img = Image.open(doc_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Content tamper
        draw.rectangle([50, 250, 400, 280], fill="white")
        draw.text((60, 255), "TAMPERED NAME - FORGED", fill="red")

        path = TAMPERED_DIR / f"{doc_path.stem}_tampered.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        img.save(path, format="PNG")
        total += 1

    return total


# ============================================================
# 5. BLOCKCHAIN RECORDS
# ============================================================

def build_blockchain(num_docs=100000):
    """Build a 100,000-block ledger (1980-2025 documents + certified copies)."""
    BLOCKCHAIN_PATH.parent.mkdir(parents=True, exist_ok=True)
    ledger = BlockchainLedger(ledger_path=str(BLOCKCHAIN_PATH))

    total = 0
    for i in range(num_docs):
        year = 1980 + (i % 45)
        doc_id = f"LK-{year}-{i:08d}"
        content_hash = hashlib.sha256(f"content_{i}".encode()).hexdigest()
        sig_hash = hashlib.sha256(f"sig_{i}".encode()).hexdigest()

        ledger.add_document(
            doc_id=doc_id,
            content_hash=content_hash,
            sig_hash=sig_hash,
            issued_at=f"{year}-01-01T00:00:00Z",
        )
        total += 1

        # Certified copy every 10th (supervisor comment)
        if i % 10 == 0 and i > 0:
            try:
                ledger.add_certified_copy(doc_id, certifier="GovLK")
                total += 1
            except Exception:
                pass

    return total


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("  RQ3 Dataset Collection (Only RQ3-relevant data)")
    print("=" * 70)

    # Create all directories
    for d in [DOCS_DIR, SIGS_DIR, REFS_DIR, DEG_DIR, TAMPERED_DIR, BLOCKCHAIN_PATH.parent]:
        d.mkdir(parents=True, exist_ok=True)

    # Create sub-folders for degradations
    for sub in ["blur", "aging", "low_dpi"]:
        (DEG_DIR / sub).mkdir(parents=True, exist_ok=True)

    # 1. Documents
    print("\n[1/5] Generating synthetic documents (1,000)...")
    count = generate_documents(num_per_type=200)
    print(f"   [OK] {count} documents")

    # 2. Signatures + References
    print("\n[2/5] Generating signature regions + references...")
    total_sigs = 0
    for script in SIGNATURE_SCRIPTS:
        c = generate_signatures(script, num_signers=100)
        total_sigs += c
        print(f"   [OK] {script}: {c} files (100 sig + 100 ref)")
    print(f"   Total: {total_sigs} signature files")

    # 3. Degradations
    print("\n[3/5] Applying degradations (3 types)...")
    count = apply_degradations(num_docs=1000)
    print(f"   [OK] {count} degraded images")

    # 4. Tampered
    print("\n[4/5] Generating tampered documents (500)...")
    count = generate_tampered(num_docs=500)
    print(f"   [OK] {count} tampered documents")

    # 5. Blockchain
    print("\n[5/5] Building blockchain (100,000 records)...")
    print("   [WARN] This may take 2-3 minutes...")
    count = build_blockchain(num_docs=100000)
    print(f"   [OK] {count} blockchain blocks")

    # Summary
    print("\n" + "=" * 70)
    print("  RQ3 DATASET COMPLETE")
    print("=" * 70)
    print(f"\nOutput: {DATA_DIR.absolute()}")
    print(f"\nDataset summary:")
    print(f"   Documents:            1,000")
    print(f"   Signature regions:    300")
    print(f"   Reference signatures: 300")
    print(f"   Degraded documents:   3,000")
    print(f"   Tampered documents:   500")
    print(f"   Blockchain blocks:    {count:,}")
    print(f"\nTotal records: ~115,000")
    print()


if __name__ == "__main__":
    main()