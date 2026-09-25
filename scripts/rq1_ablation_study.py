"""RQ1 Ablation Study — Threshold variations (සැබෑ)."""
import sys
import json
import numpy as np
import cv2
import torch
import random
from pathlib import Path
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score, precision_score, recall_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.siamese import SiameseNetwork
from src.research.experiment_tracker import AblationStudy, DataVersioner

# ============================================================
# CONFIG
# ============================================================
MODEL_PATH = Path('models/checkpoints/sigguard_v2/best_model.pth')
TEST_DIR = Path('data/splits_v2/test')
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# Load model
checkpoint = torch.load(MODEL_PATH, map_location='cpu')
model = SiameseNetwork(embedding_dim=128, backbone='resnet18', pretrained=False)
model.load_state_dict(checkpoint['model_state_dict'])
model = model.to(DEVICE)
model.eval()

print(f'Model: Epoch {checkpoint["epoch"]}, Val loss {checkpoint["val_loss"]:.4f}')
print(f'Device: {DEVICE}')

def load_img(path):
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        img = np.ones((224, 224), dtype=np.uint8) * 255
    img = cv2.resize(img, (224, 224))
    img = img.astype(np.float32) / 255.0
    return torch.from_numpy(img).unsqueeze(0).repeat(3, 1, 1)

# ============================================================
# CREATE TEST PAIRS
# ============================================================
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

print(f'\nTest pairs: {len(all_pairs)}')

# ============================================================
# COMPUTE DISTANCES (once)
# ============================================================
print('Computing distances...')
all_labels = []
all_dists = []

with torch.no_grad():
    for img1_path, img2_path, label in all_pairs:
        img1 = load_img(img1_path).unsqueeze(0).to(DEVICE)
        img2 = load_img(img2_path).unsqueeze(0).to(DEVICE)
        emb1, emb2 = model(img1, img2)
        d = torch.nn.functional.pairwise_distance(emb1, emb2).item()
        all_labels.append(label)
        all_dists.append(d)

all_labels = np.array(all_labels)
all_dists = np.array(all_dists)

# ============================================================
# EVALUATE FUNCTION
# ============================================================
def evaluate_threshold(config):
    """Evaluate with different thresholds."""
    threshold = config.get('threshold', 0.1358)
    preds = (all_dists > threshold).astype(int)

    return {
        'accuracy': float(accuracy_score(all_labels, preds)),
        'precision': float(precision_score(all_labels, preds, zero_division=0)),
        'recall': float(recall_score(all_labels, preds, zero_division=0)),
        'f1': float(f1_score(all_labels, preds, zero_division=0)),
        'auc_roc': float(roc_auc_score(all_labels, all_dists)),
    }

# ============================================================
# RUN ABLATION STUDY
# ============================================================
base_config = {'threshold': 0.1358}

ablation = AblationStudy(base_config=base_config)

results = ablation.run(
    variations={
        'threshold': [0.08, 0.10, 0.11, 0.12, 0.1358, 0.15, 0.18, 0.20, 0.25],
    },
    evaluate_fn=evaluate_threshold,
)

print()
print(ablation.summary())
print()

# ============================================================
# SAVE RESULTS
# ============================================================
output = {
    'ablation_results': results,
    'best_threshold': ablation.best_value('threshold'),
    'test_pairs': len(all_pairs),
}

output_file = Path('docs/rq1_ablation_study.json')
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print(f'Results saved: {output_file}')
print()

# ============================================================
# BEST THRESHOLD ANALYSIS
# ============================================================
print('=' * 60)
print('BEST THRESHOLD ANALYSIS')
print('=' * 60)

best_threshold = ablation.best_value('threshold')
print(f'Best threshold: {best_threshold}')

best_result = None
for r in results['threshold']:
    if r['value'] == best_threshold:
        best_result = r['metrics']
        break

if best_result:
    print(f'Best accuracy: {best_result["accuracy"]:.4f}')
    print(f'Best F1: {best_result["f1"]:.4f}')
    print(f'Best precision: {best_result["precision"]:.4f}')
    print(f'Best recall: {best_result["recall"]:.4f}')