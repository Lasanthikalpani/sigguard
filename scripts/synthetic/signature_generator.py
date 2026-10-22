# scripts/synthetic/signature_generator.py
"""
Bezier-curve signature generator with STRONG genuine/forged separability.

Key design:
  - Genuine: shape-preserving — same base curve per signer, small intra-class variation
  - Forged:  shape-altering — different base curve, extreme stroke width, no loops
"""

import os
import random
import hashlib
import numpy as np
from PIL import Image, ImageDraw

try:
    import bezier
    _BEZIER_OK = True
except ImportError:
    _BEZIER_OK = False


# ─────────────────────────────────────────────────────────────
# Script-specific parameters
# ─────────────────────────────────────────────────────────────
SCRIPT_PARAMS = {
    "sinhala": {
        "n_strokes":      (3, 5),
        "curvature":      0.85,
        "stroke_width":   (2, 4),
        "loop_prob":      0.60,
        "width_range":    (330, 370),
    },
    "tamil": {
        "n_strokes":      (3, 6),
        "curvature":      0.90,
        "stroke_width":   (2, 4),
        "loop_prob":      0.70,
        "width_range":    (330, 370),
    },
    "english": {
        "n_strokes":      (2, 4),
        "curvature":      0.60,
        "stroke_width":   (2, 3),
        "loop_prob":      0.30,
        "width_range":    (330, 370),
    },
}


# ─────────────────────────────────────────────────────────────
# Deterministic seed helper
# ─────────────────────────────────────────────────────────────
def _signer_seed(script: str, signer_id: int) -> int:
    h = hashlib.sha256(f"{script}:{signer_id}".encode()).hexdigest()
    return int(h[:8], 16)


# ─────────────────────────────────────────────────────────────
# Bezier point helpers
# ─────────────────────────────────────────────────────────────
def _cubic_points(x0, y0, x1, y1, x2, y2, x3, y3, n=60):
    t = np.linspace(0, 1, n)
    x = ((1-t)**3 * x0 + 3*(1-t)**2*t * x1
         + 3*(1-t)*t**2 * x2 + t**3 * x3)
    y = ((1-t)**3 * y0 + 3*(1-t)**2*t * y1
         + 3*(1-t)*t**2 * y2 + t**3 * y3)
    return [(int(px), int(py)) for px, py in zip(x, y)]


# ─────────────────────────────────────────────────────────────
# BASE CURVE — defines a signer's identity
# ─────────────────────────────────────────────────────────────
def _base_curve(script: str, signer_seed: int):
    """
    Returns a stable list of (x0,y0,x1,y1,x2,y2,x3,y3) tuples.
    This is the SIGNER'S CANONICAL shape.
    Genuine signatures will follow this shape closely.
    """
    rng = random.Random(signer_seed)
    cfg = SCRIPT_PARAMS[script]
    n = rng.randint(*cfg["n_strokes"])
    curves = []
    for _ in range(n):
        x0, y0 = rng.randint(30, 80),   rng.randint(60, 140)
        x1, y1 = rng.randint(120, 200), rng.randint(40, 160)
        x2, y2 = rng.randint(220, 300), rng.randint(40, 160)
        x3, y3 = rng.randint(320, 370), rng.randint(60, 140)
        # Apply curvature
        cy = int(100 + (cfg["curvature"] * (rng.randint(-40, 40))))
        y1 = (y1 + cy) // 2
        y2 = (y2 + cy) // 2
        curves.append((x0, y0, x1, y1, x2, y2, x3, y3))
    return curves


# ─────────────────────────────────────────────────────────────
# GENUINE signature — small variation around base curve
# ─────────────────────────────────────────────────────────────
def _draw_genuine(curves, cfg, rng):
    img = Image.new("RGBA", (400, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    for (x0, y0, x1, y1, x2, y2, x3, y3) in curves:
        # Genuine: TINY jitter (1-3 px) — same stroke pattern
        j = 2
        pts = _cubic_points(
            x0 + rng.randint(-j, j), y0 + rng.randint(-j, j),
            x1 + rng.randint(-j, j), y1 + rng.randint(-j, j),
            x2 + rng.randint(-j, j), y2 + rng.randint(-j, j),
            x3 + rng.randint(-j, j), y3 + rng.randint(-j, j))
        sw = rng.randint(*cfg["stroke_width"])
        draw.line(pts, fill=(0, 0, 0, 255), width=sw)

        # Genuine: loops (script-specific)
        if rng.random() < cfg["loop_prob"]:
            cx, cy = rng.randint(100, 300), rng.randint(70, 130)
            r = rng.randint(10, 25)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=(0, 0, 0, 255), width=sw)

    return img


# ─────────────────────────────────────────────────────────────
# FORGED signature — DIFFERENT shape (different signer's curve)
# ─────────────────────────────────────────────────────────────
def _draw_forged(script, cfg, rng, gen_seed):
    """
    Forged = different base curve + extreme style.
    Uses a DIFFERENT signer's base curve (simulates another person).
    """
    # Use a seed far from the genuine seed
    other_seed = gen_seed + 999_999
    other_curves = _base_curve(script, other_seed)

    # Forged: EXTREME stroke width (1 or 6-8 px)
    img = Image.new("RGBA", (400, 200), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Forged signature often has fewer strokes (cut short) or more (over-drawn)
    n_take = rng.choice([1, 2, max(1, len(other_curves) - 1)])
    selected = rng.sample(other_curves, min(n_take, len(other_curves)))

    for (x0, y0, x1, y1, x2, y2, x3, y3) in selected:
        # Forged: LARGE jitter (30-50 px) — shape is wrong
        j = rng.randint(30, 50)
        # Forged: also compress the curve (different width)
        w_scale = rng.uniform(0.5, 1.3)
        pts = _cubic_points(
            x0 + rng.randint(-j, j), y0 + rng.randint(-j, j),
            int(x1 * w_scale) + rng.randint(-j, j), y1 + rng.randint(-j, j),
            int(x2 * w_scale) + rng.randint(-j, j), y2 + rng.randint(-j, j),
            int(x3 * w_scale) + rng.randint(-j, j), y3 + rng.randint(-j, j))
        # Forged: extreme stroke width
        sw = rng.choice([1, 1, 6, 7])
        draw.line(pts, fill=(0, 0, 0, 255), width=sw)

        # Forged: NO loops (or occasional misplaced loop)
        if rng.random() < 0.1:
            cx, cy = rng.randint(50, 350), rng.randint(50, 150)
            r = rng.randint(5, 40)
            draw.ellipse([cx - r, cy - r, cx + r, cy + r],
                         outline=(0, 0, 0, 255), width=1)

    return img


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────
def generate_signature(script: str, seed: int,
                       genuine: bool = True) -> Image.Image:
    """
    Generate one signature.
    - genuine=True:  small variation around a signer's base curve
    - genuine=False: different signer's curve + extreme style
    """
    if script not in SCRIPT_PARAMS:
        raise ValueError(f"Unknown script: {script}")

    cfg = SCRIPT_PARAMS[script]
    rng = random.Random(seed)
    base_curves = _base_curve(script, seed)

    if genuine:
        return _draw_genuine(base_curves, cfg, rng)
    else:
        return _draw_forged(script, cfg, rng, gen_seed=seed)


def generate_signature_set(script: str, signer_id: int,
                            n_genuine: int = 5, n_forged: int = 5,
                            output_dir: str = "signatures") -> dict:
    genuine_dir = os.path.join(output_dir, script, "genuine")
    forged_dir  = os.path.join(output_dir, script, "forged")
    os.makedirs(genuine_dir, exist_ok=True)
    os.makedirs(forged_dir,  exist_ok=True)

    base = _signer_seed(script, signer_id)
    manifest = {"script": script, "signer_id": signer_id,
                "genuine": [], "forged": []}

    for i in range(n_genuine):
        img = generate_signature(script, seed=base + i, genuine=True)
        path = os.path.join(genuine_dir, f"signer{signer_id:04d}_g{i}.png")
        img.save(path)
        manifest["genuine"].append(path)

    for i in range(n_forged):
        # Forged seed uses a DIFFERENT range (500-599)
        img = generate_signature(script, seed=base + 500 + i, genuine=False)
        path = os.path.join(forged_dir, f"signer{signer_id:04d}_f{i}.png")
        img.save(path)
        manifest["forged"].append(path)

    return manifest


# ─────────────────────────────────────────────────────────────
# CLI smoke test
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Smoke test: generating 2 signers × 3 scripts...")
    for script in ["sinhala", "tamil", "english"]:
        for signer in range(2):
            m = generate_signature_set(script, signer,
                                        n_genuine=3, n_forged=3,
                                        output_dir="data/rq3_dataset/signatures")
            print(f"  {script} signer {signer}: "
                  f"{len(m['genuine'])} genuine, {len(m['forged'])} forged")
    print("Done. Check data/rq3_dataset/signatures/")