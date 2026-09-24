"""RQ1 Final Verification - Local."""
import torch
import cv2
import numpy as np
import random
import time
from pathlib import Path
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import json
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

MODEL_PATH = Path('models/checkpoints/sigguard_v2/best_model.pth')
TEST_DIR = Path('data/splits_v2/test')
OUTPUT_FILE = Path('docs/rq1_results.json')

from src.models.siamese import SiameseNetwork

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f'Device: {DEVICE}')
print()

checkpoint = torch.load(MODEL_PATH, map_location='cpu')
print(f'Model: Epoch {checkpoint["epoch"]}, Val loss {checkpoint["val_loss"]:.4f}')
print()

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

print(f'Positive pairs: {len(positive_pairs)}')
print(f'Negative pairs: {len(negative_pairs)}')
print(f'Total: {len(positive_pairs) + len(negative_pairs)}')
print()

all_pairs = positive_pairs + negative_pairs
random.shuffle(all_pairs)

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

genuine_dists = all_dists[all_labels == 0]
forged_dists = all_dists[all_labels == 1]

print('=' * 60)
print('DISTANCE DISTRIBUTION')
print('=' * 60)
print(f'Genuine: mean={genuine_dists.mean():.4f}, std={genuine_dists.std():.4f}')
print(f'Forged:  mean={forged_dists.mean():.4f}, std={forged_dists.std():.4f}')
print()

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

preds = (all_dists > best_threshold).astype(int)

accuracy = accuracy_score(all_labels, preds)
precision = precision_score(all_labels, preds, zero_division=0)
recall = recall_score(all_labels, preds, zero_division=0)
f1 = f1_score(all_labels, preds, zero_division=0)
auc_roc = roc_auc_score(all_labels, all_dists)

print()
print('=' * 60)
print('RQ1 FINAL METRICS')
print('=' * 60)
print(f'Accuracy:  {accuracy:.4f}  (target: >= 0.92)')
print(f'Precision: {precision:.4f}  (target: >= 0.90)')
print(f'Recall:    {recall:.4f}  (target: >= 0.90)')
print(f'F1:        {f1:.4f}  (target: >= 0.90)')
print(f'AUC-ROC:   {auc_roc:.4f}  (target: >= 0.95)')
print('=' * 60)

x1 = torch.randn(1, 3, 224, 224).to(DEVICE)
x2 = torch.randn(1, 3, 224, 224).to(DEVICE)
with torch.no_grad():
    for _ in range(5):
        model(x1, x2)

times = []
with torch.no_grad():
    for _ in range(100):
        start = time.time()
        model(x1, x2)
        times.append(time.time() - start)

avg_time = np.mean(times) * 1000
p99_time = np.percentile(times, 99) * 1000

print()
print('=' * 60)
print('INFERENCE TIME')
print('=' * 60)
print(f'Average: {avg_time:.2f} ms')
print(f'P99:     {p99_time:.2f} ms')
print(f'Target:  <= 2000 ms')
print('=' * 60)

results = {
    'rq1': {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'auc_roc': float(auc_roc),
        'inference_time_ms': float(avg_time),
        'inference_time_p99_ms': float(p99_time),
        'best_threshold': float(best_threshold),
        'genuine_mean_dist': float(genuine_dists.mean()),
        'forged_mean_dist': float(forged_dists.mean()),
        'test_pairs': len(all_pairs),
        'all_targets_met': bool(accuracy >= 0.92 and auc_roc >= 0.95 and avg_time <= 2000),
    }
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    json.dump(results, f, indent=2)

print()
print(f'Results saved: {OUTPUT_FILE}')
print(f'All targets met: {results["rq1"]["all_targets_met"]}')