# scripts/synthetic/degradation.py

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

def degrade_aging(img: Image.Image, severity: float = 0.5) -> Image.Image:
    """Yellowing + brown spots + faded text."""
    arr = np.array(img).astype(np.float32)
    # Yellow tint
    arr[:, :, 2] *= (1 - 0.3 * severity)  # reduce blue
    arr[:, :, 1] *= (1 - 0.1 * severity)
    # Add brown spots
    h, w = arr.shape[:2]
    n_spots = int(50 * severity)
    for _ in range(n_spots):
        cx, cy = np.random.randint(0, w), np.random.randint(0, h)
        r = np.random.randint(5, 25)
        yy, xx = np.ogrid[:h, :w]
        mask = (xx - cx)**2 + (yy - cy)**2 <= r**2
        arr[mask] = arr[mask] * 0.7 + np.array([120, 80, 40]) * 0.3
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

def degrade_blur(img: Image.Image, radius: int = 3) -> Image.Image:
    return img.filter(ImageFilter.GaussianBlur(radius=radius))

def degrade_low_dpi(img: Image.Image, target_dpi: int = 150) -> Image.Image:
    """Simulate low-DPI scan by downsampling then upsampling."""
    w, h = img.size
    scale = target_dpi / 600
    small = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return small.resize((w, h), Image.LANCZOS)