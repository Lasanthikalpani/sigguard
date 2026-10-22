# scripts/synthetic/check_signature_quality.py
"""
Quality check using SIGNATURE-SPECIFIC pHash (not imagehash).
"""

import glob
import re
import numpy as np
from PIL import Image
from itertools import combinations
from scripts.synthetic.signature_phash import signature_phash, signature_hamming


def _signer_id(path: str) -> int:
    m = re.search(r"signer(\d+)_", path)
    return int(m.group(1)) if m else -1


def check(script: str):
    genuine_files = sorted(glob.glob(
        f"data/rq3_dataset/signatures/{script}/genuine/*.png"))
    forged_files = sorted(glob.glob(
        f"data/rq3_dataset/signatures/{script}/forged/*.png"))

    if not genuine_files or not forged_files:
        print(f"{script:8s}  ⚠️  missing files")
        return None

    by_signer_g, by_signer_f = {}, {}
    for p in genuine_files:
        by_signer_g.setdefault(_signer_id(p), []).append(p)
    for p in forged_files:
        by_signer_f.setdefault(_signer_id(p), []).append(p)

    g_dists, f_dists = [], []
    for sid, files in by_signer_g.items():
        hashes = [signature_phash(Image.open(p)) for p in files]
        for a, b in combinations(hashes, 2):
            g_dists.append(signature_hamming(a, b))

    for sid in by_signer_g:
        if sid not in by_signer_f:
            continue
        g_hashes = [signature_phash(Image.open(p)) for p in by_signer_g[sid]]
        f_hashes = [signature_phash(Image.open(p)) for p in by_signer_f[sid]]
        for gh in g_hashes:
            for fh in f_hashes:
                f_dists.append(signature_hamming(gh, fh))

    if not g_dists or not f_dists:
        print(f"{script:8s}  ⚠️  insufficient pairs")
        return None

    g_mean = np.mean(g_dists)
    f_mean = np.mean(f_dists)
    gap = f_mean - g_mean
    status = "✅" if gap >= 10 else "⚠️"
    print(f"{script:8s}  genuine-genuine: {g_mean:5.1f} bits  "
          f"genuine-forged: {f_mean:5.1f} bits  "
          f"gap: {gap:5.1f}  {status}  (n_g={len(g_dists)}, n_f={len(f_dists)})")
    return gap


if __name__ == "__main__":
    print("=" * 80)
    print("Signature quality check — SIGNATURE-SPECIFIC pHash")
    print("=" * 80)
    gaps = []
    for script in ["sinhala", "tamil", "english"]:
        g = check(script)
        if g is not None:
            gaps.append(g)
    print("=" * 80)
    if gaps:
        print(f"Overall gap: {np.mean(gaps):.1f} bits  "
              f"{'✅ PASS' if np.mean(gaps) >= 10 else '❌ FAIL'}")