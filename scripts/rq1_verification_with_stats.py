"""RQ1 Verification with Statistical Validation."""
import sys
import json
import random
import numpy as np
import cv2
import torch
from pathlib import Path
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.siamese import SiameseNetwork
from src.evaluation.statistical_validation import StatisticalValidator

MODEL_PATH = Path('models/checkpoints/sigguard_v2/best_model.pth')
TEST_DIR = Path('data/splits_v2/test')
OUTPUT_FILE = Path('docs/rq1_results_with_stats.json')

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load model
checkpoint = torch.load(MODEL_PATH, map_location='cpu')
print(f'Model: Epoch {checkpoint["epoch"]}, Val loss {checkpoint["val_loss"]:.4f}')

model = SiameseNetwork(embedding_dim=128, backbone='resnet18', pretrained=False)
model.load_state_dict(checkpoint['model_state_dict'])
model = model.to(DEVICE)
model.eval()

def load_img(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        img = np.ones((224, 224), dtype=np.uint8) * 255
    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32) / 255.0
    return torch.from_numpy(img).unsqueeze(0).repeat(3, 1, 1)

# Create test pairs
genuine_dir = TEST_DIR / 'genuine'
forged_dir = TEST_DIR / 'forged'

random.seed(42)
N_PAIRS = 200

positive_pairs = []
for signer_dir in sorted(genuine_dir.iterdir()):
    if signer_dir.is_dir():
        images = list(signer_dir.glob('*.png'))
        if len(images) >= 2:
            for i in range(len(images)):
                for j in range(i + 1, len(images)):
                    if len(positive_pairs) < N_PAIRS:
                        positive_pairs.append((images[i], images[j], 0))

negative_pairs = []
for signer_dir in sorted(genuine_dir.iterdir()):
    if signer_dir.is_dir():
        forged_signer_dir = forged_dir / signer_dir.name
        if not forged_signer_dir.exists():
            continue
        genuine_imgs = list(signer_dir.glob('*.png'))
        forged_imgs = list(forged_signer_dir.glob('*.png'))
        for g in genuine_imgs:
            for f in forged_imgs:
                if len(negative_pairs) < N_PAIRS:
                    negative_pairs.append((g, f, 1))

all_pairs = positive_pairs + negative_pairs
random.shuffle(all_pairs)

print(f'Positive pairs: {len(positive_pairs)}')
print(f'Negative pairs: {len(negative_pairs)}')
print(f'Total pairs: {len(all_pairs)}')
print()

# Evaluate
all_labels = []
all_dists = []

with torch.no_grad():
    for img1_path, img2_path, label in all_pairs:
        img1 = load_img(img1_path).unsqueeze(0).to(DEVICE)
        img2 = load_img(img2_path).unsqueeze(0).to(DEVICE)
        emb1, emb2 = model(img1, img2)
        distance = torch.nn.functional.pairwise_distance(emb1, emb2).item()
        all_labels.append(label)
        all_dists.append(distance)

all_labels = np.array(all_labels)
all_dists = np.array(all_dists)

# Optimal threshold
thresholds = np.linspace(all_dists.min(), all_dists.max(), 200)
best_f1 = 0
best_threshold = 0
for thresh in thresholds:
    preds = (all_dists > thresh).astype(int)
    f1 = f1_score(all_labels, preds, zero_division=0)
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = thresh

print(f'Best threshold: {best_threshold:.4f}')
print(f'Best F1: {best_f1:.4f}')
print()
# Distance distribution analysis
genuine_dists = all_dists[all_labels == 0]
forged_dists = all_dists[all_labels == 1]

print()
print('=' * 60)
print('DISTANCE DISTRIBUTION')
print('=' * 60)
print(f'Genuine pairs (label=0): n={len(genuine_dists)}, '
      f'mean={genuine_dists.mean():.4f}, std={genuine_dists.std():.4f}')
print(f'Forged pairs  (label=1): n={len(forged_dists)}, '
      f'mean={forged_dists.mean():.4f}, std={forged_dists.std():.4f}')
print()

# Overlap analysis
threshold = best_threshold
genuine_above = (genuine_dists > threshold).sum()
forged_below = (forged_dists < threshold).sum()

print(f'Threshold: {threshold:.4f}')
print(f'Genuine above threshold (FP): {genuine_above}/{len(genuine_dists)}')
print(f'Forged below threshold (FN):  {forged_below}/{len(forged_dists)}')
print()

# AUC-ROC calculation explanation
from sklearn.metrics import roc_auc_score
print(f'AUC-ROC (with all_dists):      {roc_auc_score(all_labels, all_dists):.4f}')
print(f'AUC-ROC (with -all_dists):     {roc_auc_score(all_labels, -all_dists):.4f}')
print('=' * 60)
print()
# Predictions
all_preds = (all_dists > best_threshold).astype(int)
# For AUC-ROC: probability that sample is FORGED (label=1)
# Higher distance → Higher probability of being forged
all_probs = all_dists / (all_dists.max() + 1e-8)

# Baseline (random)
np.random.seed(42)
baseline_preds = np.random.randint(0, 2, len(all_labels))

# Statistical validation
validator = StatisticalValidator(
    y_true=all_labels,
    y_pred=all_preds,
    y_prob=all_probs,
    y_pred_baseline=baseline_preds,
)

validator.print_report()

# Save results
results = {
    'rq1': {
        'threshold': float(best_threshold),
        'f1': float(best_f1),
        'statistical_validation': validator.report(),
    }
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    json.dump(results, f, indent=2)

print(f'\nResults saved: {OUTPUT_FILE}')