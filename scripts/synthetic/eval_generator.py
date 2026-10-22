# scripts/synthetic/eval_generator.py
import os
import random
from PIL import Image, ImageDraw
import sys

# Project Root එකට access
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

def generate_eval_set(output_dir: str = "data/rq3_dataset", full: bool = False):
    """
    Generate RQ3 evaluation set:
    - certified_copies
    - forged_copies
    - originals
    - photocopies
    """
    n = 100 if full else 10
    base_dir = os.path.join(output_dir, "rq3_layer6_eval")
    
    classes = ["certified_copies", "forged_copies", "originals", "photocopies"]
    for c in classes:
        os.makedirs(os.path.join(base_dir, c), exist_ok=True)
    
    for i in range(n):
        # Original image
        img = Image.new('RGB', (400, 400), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((50, 50), f"Document {i}", fill='black')
        draw.rectangle([(200, 200), (300, 300)], outline='black')
        
        # Save to each class
        img.save(os.path.join(base_dir, "originals", f"original_{i}.png"))
        img.save(os.path.join(base_dir, "certified_copies", f"cert_copy_{i}.png"))
        
        # Forged (slightly modified)
        forged = img.copy()
        draw = ImageDraw.Draw(forged)
        draw.rectangle([(250, 250), (350, 350)], outline='red')
        forged.save(os.path.join(base_dir, "forged_copies", f"forged_{i}.png"))
        
        # Photocopy (slightly blurred/noisy)
        photocopy = img.copy()
        photocopy = photocopy.resize((300, 300)).resize((400, 400))
        photocopy.save(os.path.join(base_dir, "photocopies", f"photo_{i}.png"))
    
    print(f"  Generated {n} images per class in {base_dir}")

if __name__ == "__main__":
    generate_eval_set(full=True)