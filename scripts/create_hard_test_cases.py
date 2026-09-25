"""Create hard test cases for SigGuard testing."""
import cv2
import numpy as np
from pathlib import Path

def create_hard_negatives(source_dir, output_dir, n_per_image=4):
    """Create hard negatives (very similar forgeries)."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    genuine_imgs = list(Path(source_dir).glob('*.png'))[:5]
    count = 0

    for img_path in genuine_imgs:
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        for j in range(n_per_image):
            h, w = img.shape
            angle = np.random.uniform(-5, 5)
            M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
            rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
            cv2.imwrite(str(output_path / f'hard_neg_{img_path.stem}_{j:02d}.png'), rotated)
            count += 1

    return count

def create_hard_positives(source_dir, output_dir, n=20):
    """Create hard positives (very different genuine)."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    genuine_imgs = list(Path(source_dir).glob('*.png'))
    count = 0

    for i in range(n):
        img_path = np.random.choice(genuine_imgs)
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        h, w = img.shape
        angle = np.random.uniform(-20, 20)
        M = cv2.getRotationMatrix2D((w//2, h//2), angle, 1.0)
        rotated = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
        cv2.imwrite(str(output_path / f'hard_pos_{i:03d}.png'), rotated)
        count += 1

    return count

# Find first test signer
test_genuine_dir = Path('data/splits/test/genuine')
signers = sorted([d for d in test_genuine_dir.iterdir() if d.is_dir()])

if signers:
    first_signer = signers[0]
    print(f'Using signer: {first_signer.name}')

    hard_neg = create_hard_negatives(
        str(first_signer),
        'data/test_data/02_hard_cases/hard_negatives',
    )
    hard_pos = create_hard_positives(
        str(first_signer),
        'data/test_data/02_hard_cases/hard_positives',
    )

    print(f'Created {hard_neg} hard negatives')
    print(f'Created {hard_pos} hard positives')
else:
    print('No signers found')
