"""
RQ3 Test Data Generator

Generates synthetic Sri Lankan government documents + signatures for testing.
"""
import io
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent.parent))

random.seed(42)

OUTPUT_DIR = Path("test_data")
DOCUMENTS_DIR = OUTPUT_DIR / "documents"
SIGNATURES_DIR = OUTPUT_DIR / "signatures"
FORGED_DIR = OUTPUT_DIR / "forged"
TAMPERED_DIR = OUTPUT_DIR / "tampered"
BATCHES_DIR = OUTPUT_DIR / "batches"

DOCUMENT_TYPES = [
    ("land_deed", "Land Deed", 1000, 700),
    ("id_card", "National Identity Card", 850, 550),
    ("birth_cert", "Birth Certificate", 1000, 750),
    ("degree", "Degree Certificate", 1100, 800),
    ("vehicle_reg", "Vehicle Registration", 900, 600),
]

SIGNATURE_STYLES = [
    ("sinhala", "Sinhala signature"),
    ("tamil", "Tamil signature"),
    ("english", "English signature"),
    ("mixed_1", "Mixed Sinhala-English"),
    ("mixed_2", "Mixed Tamil-English"),
]


def get_font(size):
    for font_name in ["arial.ttf", "calibri.ttf", "times.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(font_name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def create_document(doc_type, title, width, height, doc_id):
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    
    draw.rectangle([10, 10, width - 10, height - 10], outline="darkblue", width=3)
    draw.rectangle([15, 15, width - 15, height - 15], outline="gold", width=1)
    
    header_font = get_font(28)
    sub_font = get_font(16)
    body_font = get_font(14)
    small_font = get_font(12)
    
    draw.ellipse([40, 40, 100, 100], outline="darkblue", width=2)
    draw.ellipse([50, 50, 90, 90], fill="gold", outline="darkblue", width=1)
    draw.text((70, 75), "LK", font=get_font(20), fill="darkblue", anchor="mm")
    
    draw.text((width // 2, 60), "DEMOCRATIC SOCIALIST REPUBLIC OF SRI LANKA",
              font=sub_font, fill="darkblue", anchor="mm")
    draw.text((width // 2, 100), title.upper(), font=header_font, fill="darkblue", anchor="mm")
    
    draw.line([(30, 130), (width - 30, 130)], fill="darkblue", width=2)
    
    draw.text((40, 150), f"Document ID: {doc_id}", font=body_font, fill="black")
    draw.text((40, 175), f"Issued: 2026-09-28", font=body_font, fill="black")
    draw.text((40, 200), f"Serial No: {random.randint(100000, 999999)}", font=body_font, fill="black")
    
    y = 250
    fields = [
        ("Name:", f"Mr./Mrs. {random.choice(['K. Perera', 'S. Fernando', 'A. Silva', 'M. Jayawardena', 'R. Wickramasinghe'])}"),
        ("NIC No:", f"{random.randint(1960, 2010)}{random.randint(1000000, 9999999)}V"),
        ("Address:", random.choice(['Colombo 05', 'Matara', 'Anuradhapura', 'Kandy', 'Galle'])),
        ("District:", random.choice(['Western', 'Southern', 'Northern', 'Central', 'Eastern'])),
    ]
    
    for label, value in fields:
        draw.text((40, y), label, font=body_font, fill="gray")
        draw.text((200, y), value, font=body_font, fill="black")
        y += 30
    
    y += 20
    legal_lines = [
        "This document is issued under the authority of the Government of Sri Lanka.",
        "Any alteration, forgery, or unauthorized reproduction is a punishable offense",
        "under the Penal Code of Sri Lanka (Sections 453-462).",
        "",
        "This document is invalid without the official seal and authorized signature.",
    ]
    for line in legal_lines:
        draw.text((40, y), line, font=small_font, fill="darkgray")
        y += 18
    
    qr_area_size = 400
    margin = 20
    qr_x = width - qr_area_size - margin
    qr_y = height - qr_area_size - margin
    draw.rectangle([qr_x - 5, qr_y - 5, width - margin + 5, height - margin + 5],
                   outline="gray", width=1)
    draw.text((qr_x + qr_area_size // 2, qr_y - 15),
              "QR Integrity Code (Reserved)", font=small_font, fill="gray", anchor="mm")
    
    seal_x = width - 120
    seal_y = 180
    draw.ellipse([seal_x - 60, seal_y - 60, seal_x + 60, seal_y + 60], outline="darkred", width=3)
    draw.ellipse([seal_x - 50, seal_y - 50, seal_x + 50, seal_y + 50], outline="darkred", width=1)
    draw.text((seal_x, seal_y - 15), "OFFICIAL", font=small_font, fill="darkred", anchor="mm")
    draw.text((seal_x, seal_y + 5), "SEAL", font=small_font, fill="darkred", anchor="mm")
    draw.text((seal_x, seal_y + 25), "GOVT. OF SRI LANKA", font=get_font(8), fill="darkred", anchor="mm")
    
    sig_y = height - 100
    draw.line([(60, sig_y), (300, sig_y)], fill="black", width=1)
    draw.text((60, sig_y + 5), "Authorized Signature", font=small_font, fill="gray")
    
    return img


def create_signature(style, sig_id, variation="genuine"):
    width, height = 400, 200
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    
    style_seed = {"sinhala": 1, "tamil": 2, "english": 3, "mixed_1": 4, "mixed_2": 5}.get(style, 1)
    random.seed(sig_id * 100 + style_seed + hash(variation) % 1000)
    
    if variation == "genuine":
        jitter, stroke_width, num_strokes = 3, 3, 8
    elif variation == "skilled_forgery":
        jitter, stroke_width, num_strokes = 6, 3, 8
    elif variation == "unskilled_forgery":
        jitter, stroke_width, num_strokes = 15, 4, 10
    elif variation == "traced":
        jitter, stroke_width, num_strokes = 2, 2, 8
    else:
        jitter, stroke_width, num_strokes = 3, 3, 8
    
    base_x = 50
    base_y = 100
    current_x = base_x
    
    for i in range(num_strokes):
        points = []
        for j in range(4):
            x = current_x + j * random.randint(30, 60) + random.randint(-jitter, jitter)
            y = base_y + random.randint(-40, 40) + random.randint(-jitter, jitter)
            points.append((x, y))
        
        for k in range(len(points) - 1):
            x1, y1 = points[k]
            x2, y2 = points[k + 1]
            for t in range(20):
                t_val = t / 20.0
                x = int(x1 + (x2 - x1) * t_val + random.randint(-1, 1))
                y = int(y1 + (y2 - y1) * t_val + random.randint(-1, 1))
                draw.ellipse([x - stroke_width, y - stroke_width, x + stroke_width, y + stroke_width],
                             fill="black")
        
        current_x = points[-1][0] + random.randint(5, 20)
        if i % 3 == 2:
            current_x = base_x + random.randint(0, 30)
    
    underline_y = base_y + 60
    draw.line([(base_x, underline_y), (base_x + random.randint(200, 300), underline_y)],
              fill="black", width=2)
    
    return img


def create_tampered_document(original_img, tamper_type):
    img = original_img.copy()
    draw = ImageDraw.Draw(img)
    w, h = img.size
    
    if tamper_type == "content_change":
        draw.rectangle([200, 250, 500, 280], fill="white")
        draw.text((200, 250), "Mr./Mrs. TAMPERED NAME", font=get_font(14), fill="black")
    elif tamper_type == "qr_destroyed":
        draw.rectangle([w - 450, h - 450, w, h], fill="black")
    elif tamper_type == "seal_removed":
        draw.rectangle([w - 180, 120, w - 60, 240], fill="white")
    
    return img


def main():
    print("=" * 70)
    print("  RQ3 Test Data Generator")
    print("=" * 70)
    
    for d in [DOCUMENTS_DIR, SIGNATURES_DIR, FORGED_DIR, TAMPERED_DIR, BATCHES_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    print("\n📄 Generating 5 genuine documents...")
    documents = []
    for i, (doc_key, title, w, h) in enumerate(DOCUMENT_TYPES, start=1):
        doc_id = f"LK-TEST-{i:03d}"
        img = create_document(doc_key, title, w, h, doc_id)
        path = DOCUMENTS_DIR / f"doc_{i:02d}_{doc_key}.png"
        img.save(path, format="PNG")
        documents.append((img, doc_id, path))
        print(f"   ✅ {path.name} ({w}x{h})")
    
    print("\n✍️  Generating 5 genuine signatures...")
    signatures = []
    for i, (style_key, style_name) in enumerate(SIGNATURE_STYLES, start=1):
        img = create_signature(style_key, sig_id=i, variation="genuine")
        path = SIGNATURES_DIR / f"sig_{i:02d}_{style_key}.png"
        img.save(path, format="PNG")
        signatures.append((img, style_key, path))
        print(f"   ✅ {path.name}")
    
    print("\n🎭 Generating 5 forged signatures...")
    forgery_types = ["skilled_forgery", "unskilled_forgery", "traced",
                     "skilled_forgery", "unskilled_forgery"]
    for i, ((style_key, _), forgery) in enumerate(zip(SIGNATURE_STYLES, forgery_types), start=1):
        img = create_signature(style_key, sig_id=i, variation=forgery)
        path = FORGED_DIR / f"forged_{i:02d}_{style_key}_{forgery}.png"
        img.save(path, format="PNG")
        print(f"   ✅ {path.name} ({forgery})")
    
    print("\n🔥 Generating 3 tampered documents...")
    tamper_types = ["content_change", "qr_destroyed", "seal_removed"]
    for i, tamper in enumerate(tamper_types, start=1):
        original_img, doc_id, _ = documents[i - 1]
        tampered = create_tampered_document(original_img, tamper)
        path = TAMPERED_DIR / f"tampered_{i:02d}_{tamper}.png"
        tampered.save(path, format="PNG")
        print(f"   ✅ {path.name} ({tamper}, based on {doc_id})")
    
    print("\n📦 Generating 3 test batches...")
    
    b1 = BATCHES_DIR / "batch_1_all_genuine"
    b1.mkdir(exist_ok=True)
    for i in range(3):
        img, doc_id, _ = documents[i]
        img.save(b1 / f"doc_{i+1:02d}.png")
        sig_img, _, _ = signatures[i]
        sig_img.save(b1 / f"sig_{i+1:02d}.png")
    print(f"   ✅ batch_1_all_genuine (3 genuine pairs)")
    
    b2 = BATCHES_DIR / "batch_2_mixed"
    b2.mkdir(exist_ok=True)
    for i in range(3):
        img, doc_id, _ = documents[i]
        img.save(b2 / f"doc_{i+1:02d}.png")
        if i == 1:
            forged_img = create_signature(SIGNATURE_STYLES[i][0], sig_id=i, variation="unskilled_forgery")
            forged_img.save(b2 / f"sig_{i+1:02d}_forged.png")
        else:
            sig_img, _, _ = signatures[i]
            sig_img.save(b2 / f"sig_{i+1:02d}.png")
    print(f"   ✅ batch_2_mixed (2 genuine + 1 forged)")
    
    b3 = BATCHES_DIR / "batch_3_all_forged"
    b3.mkdir(exist_ok=True)
    for i in range(3):
        img, doc_id, _ = documents[i]
        img.save(b3 / f"doc_{i+1:02d}.png")
        forged_img = create_signature(SIGNATURE_STYLES[i][0], sig_id=i, variation="skilled_forgery")
        forged_img.save(b3 / f"sig_{i+1:02d}_forged.png")
    print(f"   ✅ batch_3_all_forged (3 forged pairs)")
    
    print("\n" + "=" * 70)
    print("  ✅ TEST DATA GENERATION COMPLETE")
    print("=" * 70)
    print(f"\n📁 Output location: {OUTPUT_DIR.absolute()}")
    print(f"\n   📄 Documents:  {len(list(DOCUMENTS_DIR.glob('*.png')))} files")
    print(f"   ✍️  Signatures: {len(list(SIGNATURES_DIR.glob('*.png')))} files")
    print(f"   🎭 Forged:     {len(list(FORGED_DIR.glob('*.png')))} files")
    print(f"   🔥 Tampered:   {len(list(TAMPERED_DIR.glob('*.png')))} files")
    print(f"   📦 Batches:    3 folders")
    print()


if __name__ == "__main__":
    main()