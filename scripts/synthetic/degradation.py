# scripts/synthetic/degradation.py

import os
from PIL import Image, ImageFilter, ImageEnhance
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)


def _create_base_document(idx: int) -> Image.Image:
    """Create a basic placeholder document image."""
    img = Image.new('RGB', (400, 400), color='white')
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.text((50, 50), f"Document {idx}", fill='black')
    draw.text((50, 100), "Name: John Doe", fill='black')
    draw.text((50, 150), "DOB: 1990-01-15", fill='black')
    return img


def generate_degraded(output_dir: str = "data/rq3_dataset", full: bool = False):
    """
    Generate degraded documents (aging, blur, low_dpi).
    """
    n = 100 if full else 10
    
    degradations = ["degraded_aging", "degraded_blur", "degraded_lowdpi"]
    
    for deg_name in degradations:
        base_dir = os.path.join(output_dir, "rq3_eval", deg_name)
        os.makedirs(base_dir, exist_ok=True)
        
        print(f"  Generating {n} {deg_name} documents...")
        
        for i in range(n):
            img = _create_base_document(i)
            
            if deg_name == "degraded_aging":
                # Yellow tint + contrast reduction
                img = ImageEnhance.Color(img).enhance(0.5)
                img = ImageEnhance.Contrast(img).enhance(0.8)
            elif deg_name == "degraded_blur":
                # Gaussian blur
                img = img.filter(ImageFilter.GaussianBlur(radius=2))
            elif deg_name == "degraded_lowdpi":
                # Downsample then upsample
                w, h = img.size
                img = img.resize((w // 4, h // 4), Image.LANCZOS)
                img = img.resize((w, h), Image.LANCZOS)
            
            img.save(os.path.join(base_dir, f"{deg_name}_{i:04d}.png"))
        
        print(f"  ✓ Generated {n} images in {base_dir}")
        