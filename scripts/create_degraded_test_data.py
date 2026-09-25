"""Create degraded test data for RQ6."""
import cv2
import numpy as np
from pathlib import Path

def apply_aging(img, severity=0.5):
    if len(img.shape) == 2:
        yellow = np.full_like(img, 30)
    else:
        yellow = np.full_like(img, [0, 20, 50])
    return cv2.addWeighted(img, 1-severity, yellow, severity, 0)

def apply_stains(img, n=5):
    h, w = img.shape[:2]
    for _ in range(n):
        x, y = np.random.randint(0, w), np.random.randint(0, h)
        cv2.circle(img, (x, y), np.random.randint(10, 40), 100, -1)
    return img

def apply_folds(img):
    h, w = img.shape[:2]
    cv2.line(img, (0, h//2), (w, h//2), 50, 3)
    return img

def apply_poor_scan(img, dpi=150):
    scale = dpi / 600
    small = cv2.resize(img, None, fx=scale, fy=scale)
    return cv2.resize(small, (img.shape[1], img.shape[0]))

# Find first test signer
test_genuine_dir = Path('data/splits/test/genuine')
signers = sorted([d for d in test_genuine_dir.iterdir() if d.is_dir()])

if not signers:
    print('No signers found')
    exit()

first_signer = signers[0]
source_dir = str(first_signer)
output_dir = Path('data/test_data/03_degraded')
output_dir.mkdir(parents=True, exist_ok=True)

levels = {
    'clean': lambda x: x,
    'slight': lambda x: apply_aging(x, 0.2),
    'moderate': lambda x: apply_stains(apply_aging(x, 0.5), 3),
    'high': lambda x: apply_poor_scan(apply_folds(apply_stains(x, 8)), 150),
}

for level_name, transform in levels.items():
    level_path = output_dir / level_name
    level_path.mkdir(exist_ok=True)

    for img_path in Path(source_dir).glob('*.png'):
        img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue
        result = transform(img)
        cv2.imwrite(str(level_path / img_path.name), result)

    count = len(list(level_path.glob('*.png')))
    print(f'{level_name}: {count} images')
