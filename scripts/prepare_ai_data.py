# scripts/prepare_ai_data.py
import os
import random
from PIL import Image, ImageEnhance, ImageFilter

SOURCE_DIR = "data/rq3_dataset/rq3_layer6_eval"
DEST_DIR = "data/ai_training_data"

os.makedirs(DEST_DIR, exist_ok=True)

def augment_image(img, variant_index):
    """Generate 1 variant per call based on variant_index."""
    # Random rotation
    angle = random.choice([0, 5, 10, -5, -10, 15, -15])
    img = img.rotate(angle)
    
    # Random brightness
    brightness = random.uniform(0.8, 1.2)
    img = ImageEnhance.Brightness(img).enhance(brightness)
    
    # Random contrast
    contrast = random.uniform(0.8, 1.3)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    
    # Random blur (scan noise simulation)
    if random.random() > 0.5:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.3, 1.0)))
    
    # Random crop & resize
    if random.random() > 0.5:
        w, h = img.size
        crop_ratio = random.uniform(0.9, 1.0)
        new_w, new_h = int(w * crop_ratio), int(h * crop_ratio)
        left = random.randint(0, w - new_w)
        top = random.randint(0, h - new_h)
        img = img.crop((left, top, left + new_w, top + new_h))
    
    return img.resize((224, 224))

classes = ["originals", "certified_copies", "photocopies", "forged_copies"]

# Target: 5000+ images total (~1250 per class)
AUGMENTATIONS_PER_IMAGE = 125  # 40 × 125 = 5000

total_originals = 0
total_generated = 0

for c in classes:
    src_class_path = os.path.join(SOURCE_DIR, c)
    dest_class_path = os.path.join(DEST_DIR, c)
    os.makedirs(dest_class_path, exist_ok=True)
    
    if not os.path.exists(src_class_path):
        print(f"Skipping {c} (source not found)")
        continue
    
    for filename in os.listdir(src_class_path):
        if filename.endswith((".png", ".jpg", ".jpeg")):
            src_path = os.path.join(src_class_path, filename)
            base_name = os.path.splitext(filename)[0]
            
            img = Image.open(src_path).convert("RGB")
            total_originals += 1
            
            # Original resized
            img.resize((224, 224)).save(
                os.path.join(dest_class_path, f"{base_name}_orig.jpg"))
            total_generated += 1
            
            # Augmented variants
            for i in range(AUGMENTATIONS_PER_IMAGE):
                variant = augment_image(img, i)
                dest_path = os.path.join(dest_class_path, f"{base_name}_aug{i:03d}.jpg")
                variant.save(dest_path, quality=85)
                total_generated += 1

print(f"Original images processed: {total_originals}")
print(f"Total images generated: {total_generated}")
print(f"Saved to: {DEST_DIR}")
