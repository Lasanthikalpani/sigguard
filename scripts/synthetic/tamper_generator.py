# scripts/synthetic/tamper_generator.py

import os
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def _create_base_document(idx: int) -> Image.Image:
    """Create a basic placeholder document image."""
    img = Image.new('RGB', (400, 400), color='white')
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), f"Document {idx}", fill='black')
    draw.text((50, 100), "Name: John Doe", fill='black')
    draw.text((50, 150), "DOB: 1990-01-15", fill='black')
    draw.rectangle([(200, 200), (300, 300)], outline='black')
    return img

def generate_tampered(output_dir: str = "data/rq3_dataset", full: bool = False):
    """Generate tampered documents."""
    n = 100 if full else 10
    base_dir = os.path.join(output_dir, "rq3_eval", "tampered_content")
    os.makedirs(base_dir, exist_ok=True)
    
    print(f"  Generating {n} tampered documents...")
    
    for i in range(n):
        img = _create_base_document(i)
        draw = ImageDraw.Draw(img)
        # Tamper: Change DOB
        draw.rectangle([(50, 140), (200, 170)], fill='white')
        draw.text((50, 150), "DOB: 1995-01-15", fill='black')
        img.save(os.path.join(base_dir, f"tampered_{i:04d}.png"))
    
    print(f"  ✓ Generated {n} tampered images in {base_dir}")

def generate_degraded(output_dir: str = "data/rq3_dataset", full: bool = False):
    """Generate degraded documents."""
    n = 100 if full else 10
    degradations = ["degraded_aging", "degraded_blur", "degraded_lowdpi"]
    
    for deg_name in degradations:
        base_dir = os.path.join(output_dir, "rq3_eval", deg_name)
        os.makedirs(base_dir, exist_ok=True)
        
        for i in range(n):
            img = _create_base_document(i)
            if deg_name == "degraded_aging":
                img = ImageEnhance.Color(img).enhance(0.5)
            elif deg_name == "degraded_blur":
                img = img.filter(ImageFilter.GaussianBlur(radius=2))
            elif deg_name == "degraded_lowdpi":
                w, h = img.size
                img = img.resize((w // 4, h // 4), Image.LANCZOS).resize((w, h), Image.LANCZOS)
            
            img.save(os.path.join(base_dir, f"{deg_name}_{i:04d}.png"))
    
    print(f"  ✓ Generated degraded images")

def generate_amendments(output_dir: str = "data/rq3_dataset", full: bool = False):
    """Generate amendment documents."""
    n = 100 if full else 10
    legit_dir = os.path.join(output_dir, "rq3_layer5_eval", "legit_amendments")
    fake_dir = os.path.join(output_dir, "rq3_layer5_eval", "fake_amendments")
    os.makedirs(legit_dir, exist_ok=True)
    os.makedirs(fake_dir, exist_ok=True)
    
    for i in range(n):
        img = _create_base_document(i)
        draw = ImageDraw.Draw(img)
        draw.text((250, 350), "AMENDED", fill='blue')
        img.save(os.path.join(legit_dir, f"legit_amend_{i:04d}.png"))
        
        img = _create_base_document(i)
        draw = ImageDraw.Draw(img)
        draw.rectangle([(50, 90), (200, 120)], fill='white')
        draw.text((50, 100), "Name: Jane Smith (FORGED)", fill='black')
        img.save(os.path.join(fake_dir, f"fake_amend_{i:04d}.png"))
    
    print(f"  ✓ Generated amendments")
    