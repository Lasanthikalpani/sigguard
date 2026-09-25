"""RQ1 Out-of-Sample Validation — සැබෑ data සමඟ."""
import sys
import json
import numpy as np
import cv2
import torch
import random
from pathlib import Path
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.siamese import SiameseNetwork
from src.evaluation.oos_validation import OutOfSampleEvaluator

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
# COMPUTE ALL DISTANCES (once)
# ============================================================
print('\nComputing distances...')

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
                        positive_pairs.append((images[i], images[j], 0, signer_dir.name))

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
                    negative_pairs.append((g, f, 1, signer_dir.name))

all_pairs = positive_pairs + negative_pairs
random.shuffle(all_pairs)

# Extract features
all_dists = []
all_labels = []
all_groups = []

# Group mapping
signer_to_id = {}
for signer_dir in sorted(genuine_dir.iterdir()):
    if signer_dir.is_dir():
        signer_to_id[signer_dir.name] = len(signer_to_id)

with torch.no_grad():
    for img1_path, img2_path, label, signer in all_pairs:
        img1 = load_img(img1_path).unsqueeze(0).to(DEVICE)
        img2 = load_img(img2_path).unsqueeze(0).to(DEVICE)
        emb1, emb2 = model(img1, img2)
        d = torch.nn.functional.pairwise_distance(emb1, emb2).item()
        all_dists.append(d)
        all_labels.append(label)
        all_groups.append(signer_to_id[signer])

all_dists = np.array(all_dists).reshape(-1, 1)
all_labels = np.array(all_labels)
all_groups = np.array(all_groups)

print(f'Test pairs: {len(all_pairs)}')
print(f'Unique signers: {len(np.unique(all_groups))}')
print()

# ============================================================
# EVALUATE FUNCTION
# ============================================================
def evaluate_fn(X_train, y_train, X_test, y_test):
    """Evaluate with distance-based threshold."""
    # Find best threshold on train
    best_f1 = 0
    best_thresh = 0.1358
    for thresh in np.linspace(X_train.min(), X_train.max(), 100):
        preds = (X_train.flatten() > thresh).astype(int)
        f1 = f1_score(y_train, preds, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = thresh

    # Evaluate on test
    preds = (X_test.flatten() > best_thresh).astype(int)
    return {
        'accuracy': float(accuracy_score(y_test, preds)),
        'f1': float(f1_score(y_test, preds, zero_division=0)),
        'auc_roc': float(roc_auc_score(y_test, X_test.flatten())),
        'threshold': float(best_thresh),
    }

# ============================================================
# RUN OOS VALIDATION
# ============================================================
evaluator = OutOfSampleEvaluator()
results = evaluator.evaluate_all(all_dists, all_labels, all_groups, evaluate_fn)

# ============================================================
# SAVE RESULTS
# ============================================================
output = {
    'oos_validation': results,
    'test_pairs': len(all_pairs),
    'unique_signers': int(len(np.unique(all_groups))),
    'timestamp': '2026-09-25',
}

output_file = Path('docs/rq1_oos_validation.json')
output_file.parent.mkdir(parents=True, exist_ok=True)
with open(output_file, 'w') as f:
    json.dump(output, f, indent=2)

print()
print(f'Results saved: {output_file}')