# scripts/synthetic/signature_phash.py
"""
Signature-specific perceptual hash.
Replaces imagehash.phash() for thin-stroke signatures.

Features (7 total, quantized to 64 bits):
  1. Ink density          (8 bits)
  2. Bounding box aspect  (8 bits)
  3. Stroke count         (8 bits)
  4. Centroid X position  (8 bits)
  5. Centroid Y position  (8 bits)
  6. Horizontal projection symmetry (8 bits)
  7. Vertical projection symmetry   (8 bits)
"""

import numpy as np
from PIL import Image


def _quantize(value: float, lo: float, hi: float, bits: int = 8) -> str:
    """Clamp and quantize a scalar to `bits` bits."""
    v = max(lo, min(hi, value))
    normalized = (v - lo) / (hi - lo + 1e-9)
    level = int(normalized * ((1 << bits) - 1))
    return format(level, f"0{bits}b")


def signature_phash(img: Image.Image) -> str:
    """
    Compute a 64-bit signature-specific hash.
    Returns a 64-character binary string.
    """
    img = img.convert("L")
    arr = np.array(img, dtype=np.uint8)

    # Binary mask (ink = 1, background = 0)
    ink = (arr < 128).astype(np.uint8)
    total_ink = int(ink.sum())
    h, w = ink.shape

    # Feature 1: Ink density
    density = total_ink / (h * w)
    f1 = _quantize(density, 0.0, 0.5, 8)

    if total_ink == 0:
        # Empty image — return all zeros
        return "0" * 64

    # Feature 2: Bounding box aspect ratio
    ys, xs = np.where(ink == 1)
    y0, y1, x0, x1 = ys.min(), ys.max(), xs.min(), xs.max()
    bbox_w = x1 - x0 + 1
    bbox_h = y1 - y0 + 1
    aspect = bbox_w / bbox_h
    f2 = _quantize(aspect, 0.5, 10.0, 8)

    # Feature 3: Stroke count (connected components)
    try:
        from scipy import ndimage
        labeled, n_components = ndimage.label(ink)
        # Filter tiny components (< 5 px = noise)
        sizes = ndimage.sum(ink, labeled, range(1, n_components + 1))
        n_strokes = int((sizes >= 5).sum())
    except ImportError:
        n_strokes = 1
    f3 = _quantize(n_strokes, 1, 20, 8)

    # Feature 4: Centroid X (normalized)
    cx = float(xs.mean()) / w
    f4 = _quantize(cx, 0.0, 1.0, 8)

    # Feature 5: Centroid Y (normalized)
    cy = float(ys.mean()) / h
    f5 = _quantize(cy, 0.0, 1.0, 8)

    # Feature 6: Horizontal projection symmetry
    h_proj = ink.sum(axis=0).astype(np.float64)  # shape (w,)
    h_proj_norm = h_proj / (h_proj.max() + 1e-9)
    h_sym = float(1.0 - np.mean(np.abs(h_proj_norm - h_proj_norm[::-1])))
    f6 = _quantize(h_sym, 0.0, 1.0, 8)

    # Feature 7: Vertical projection symmetry
    v_proj = ink.sum(axis=1).astype(np.float64)  # shape (h,)
    v_proj_norm = v_proj / (v_proj.max() + 1e-9)
    v_sym = float(1.0 - np.mean(np.abs(v_proj_norm - v_proj_norm[::-1])))
    f7 = _quantize(v_sym, 0.0, 1.0, 8)

    return f1 + f2 + f3 + f4 + f5 + f6 + f7


def signature_hamming(h1: str, h2: str) -> int:
    """Hamming distance between two 64-bit signature hashes."""
    return sum(a != b for a, b in zip(h1, h2))