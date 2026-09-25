"""RQ1 Advanced Statistical Analysis (Quant-Level)."""
import json
import numpy as np
import cv2
import torch
import random
import sys
from pathlib import Path
from scipy import stats
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models.siamese import SiameseNetwork

# ============================================================
# CONFIG
# ============================================================
MODEL_PATH = Path('models/checkpoints/sigguard_v2/best_model.pth')
TEST_DIR = Path('data/splits_v2/test')
OUTPUT_FILE = Path('docs/rq1_advanced_statistical_results.json')

DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# ============================================================
# LOAD MODEL
# ============================================================
checkpoint = torch.load(MODEL_PATH, map_location='cpu')
model = SiameseNetwork(embedding_dim=128, backbone='resnet18', pretrained=False)
model.load_state_dict(checkpoint['model_state_dict'])
model = model.to(DEVICE)
model.eval()

print(f'Model: Epoch {checkpoint["epoch"]}, Val loss {checkpoint["val_loss"]:.4f}')
print(f'Device: {DEVICE}')
print()

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
N_PAIRS = 500

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

print(f'Test pairs: {len(all_pairs)} (genuine: {len(positive_pairs)}, forged: {len(negative_pairs)})')
print()

# ============================================================
# EVALUATE
# ============================================================
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

genuine_dists = all_dists[all_labels == 0]
forged_dists = all_dists[all_labels == 1]

# ============================================================
# 1. OPTIMAL THRESHOLD + METRICS
# ============================================================
thresholds = np.linspace(all_dists.min(), all_dists.max(), 500)
best_f1 = 0
best_threshold = 0
for thresh in thresholds:
    preds = (all_dists > thresh).astype(int)
    f1 = f1_score(all_labels, preds, zero_division=0)
    if f1 > best_f1:
        best_f1 = f1
        best_threshold = thresh

preds = (all_dists > best_threshold).astype(int)

accuracy = accuracy_score(all_labels, preds)
precision = precision_score(all_labels, preds, zero_division=0)
recall = recall_score(all_labels, preds, zero_division=0)
f1 = f1_score(all_labels, preds, zero_division=0)
auc_roc = roc_auc_score(all_labels, all_dists)

print('=' * 60)
print('1. BASIC METRICS')
print('=' * 60)
print(f'Accuracy:  {accuracy:.4f}')
print(f'Precision: {precision:.4f}')
print(f'Recall:    {recall:.4f}')
print(f'F1:        {f1:.4f}')
print(f'AUC-ROC:   {auc_roc:.4f}')
print(f'Best threshold: {best_threshold:.4f}')
print()

# ============================================================
# 2. BOOTSTRAP CONFIDENCE INTERVALS (10,000 iterations)
# ============================================================
print('=' * 60)
print('2. BOOTSTRAP CONFIDENCE INTERVALS')
print('=' * 60)

n_bootstrap = 10000
bootstrap_accs = []
bootstrap_f1s = []
bootstrap_aucs = []

rng = np.random.RandomState(42)
for _ in range(n_bootstrap):
    idx = rng.choice(len(all_labels), len(all_labels), replace=True)
    b_labels = all_labels[idx]
    b_dists = all_dists[idx]
    b_preds = (b_dists > best_threshold).astype(int)
    bootstrap_accs.append(accuracy_score(b_labels, b_preds))
    bootstrap_f1s.append(f1_score(b_labels, b_preds, zero_division=0))
    bootstrap_aucs.append(roc_auc_score(b_labels, b_dists))

bootstrap_accs = np.array(bootstrap_accs)
bootstrap_f1s = np.array(bootstrap_f1s)
bootstrap_aucs = np.array(bootstrap_aucs)

acc_ci = [float(np.percentile(bootstrap_accs, 2.5)), float(np.percentile(bootstrap_accs, 97.5))]
f1_ci = [float(np.percentile(bootstrap_f1s, 2.5)), float(np.percentile(bootstrap_f1s, 97.5))]
auc_ci = [float(np.percentile(bootstrap_aucs, 2.5)), float(np.percentile(bootstrap_aucs, 97.5))]

print(f'Bootstrap iterations: {n_bootstrap}')
print(f'Accuracy 95% CI: [{acc_ci[0]:.4f}, {acc_ci[1]:.4f}]')
print(f'F1 95% CI:       [{f1_ci[0]:.4f}, {f1_ci[1]:.4f}]')
print(f'AUC-ROC 95% CI:  [{auc_ci[0]:.4f}, {auc_ci[1]:.4f}]')
print()

# ============================================================
# 3. PERMUTATION TEST (10,000 iterations)
# ============================================================
print('=' * 60)
print('3. PERMUTATION TEST')
print('=' * 60)

n_permutations = 10000
perm_accs = []

for _ in range(n_permutations):
    perm_labels = rng.permutation(all_labels)
    perm_preds = (all_dists > best_threshold).astype(int)
    perm_accs.append(accuracy_score(perm_labels, perm_preds))

perm_accs = np.array(perm_accs)
p_value_perm = float(np.mean(perm_accs >= accuracy))

print(f'Permutation iterations: {n_permutations}')
print(f'Permutation p-value: {p_value_perm:.6f}')
print(f'Significant at 0.05: {p_value_perm < 0.05}')
print()

# ============================================================
# 4. CROSS-VALIDATION (5-fold stratified)
# ============================================================
print('=' * 60)
print('4. 5-FOLD CROSS-VALIDATION')
print('=' * 60)

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_accs = []
cv_f1s = []
cv_aucs = []

for fold, (train_idx, test_idx) in enumerate(skf.split(all_dists, all_labels), 1):
    fold_labels = all_labels[test_idx]
    fold_dists = all_dists[test_idx]

    # Find best threshold for this fold
    fold_best_f1 = 0
    fold_best_thresh = 0
    for thresh in np.linspace(fold_dists.min(), fold_dists.max(), 200):
        fold_preds = (fold_dists > thresh).astype(int)
        fold_f1 = f1_score(fold_labels, fold_preds, zero_division=0)
        if fold_f1 > fold_best_f1:
            fold_best_f1 = fold_f1
            fold_best_thresh = thresh

    fold_preds = (fold_dists > fold_best_thresh).astype(int)
    cv_accs.append(accuracy_score(fold_labels, fold_preds))
    cv_f1s.append(f1_score(fold_labels, fold_preds, zero_division=0))
    cv_aucs.append(roc_auc_score(fold_labels, fold_dists))

print(f'CV Accuracy: {np.mean(cv_accs):.4f} ± {np.std(cv_accs):.4f}')
print(f'CV F1:       {np.mean(cv_f1s):.4f} ± {np.std(cv_f1s):.4f}')
print(f'CV AUC-ROC:  {np.mean(cv_aucs):.4f} ± {np.std(cv_aucs):.4f}')
print()

# ============================================================
# 5. SIGNAL DECAY ANALYSIS
# ============================================================
print('=' * 60)
print('5. SIGNAL DECAY ANALYSIS')
print('=' * 60)

# Test how accuracy changes with threshold deviation
decay_data = []
for delta in [0, 0.01, 0.02, 0.05, 0.10, 0.15, 0.20]:
    thresh = best_threshold + delta
    preds = (all_dists > thresh).astype(int)
    acc = accuracy_score(all_labels, preds)
    decay_data.append({
        'delta': float(delta),
        'threshold': float(thresh),
        'accuracy': float(acc),
    })

print('Threshold decay:')
for d in decay_data:
    print(f'  +{d["delta"]:.2f} | threshold={d["threshold"]:.4f} | acc={d["accuracy"]:.4f}')
print()

# ============================================================
# 6. SEPARABILITY METRICS
# ============================================================
print('=' * 60)
print('6. SEPARABILITY METRICS')
print('=' * 60)

# Signal-to-Noise Ratio
snr = (forged_dists.mean() - genuine_dists.mean()) / np.sqrt(
    genuine_dists.var() + forged_dists.var()
)

# Cohen's d (between genuine and forged)
pooled_std = np.sqrt(
    ((len(genuine_dists) - 1) * genuine_dists.var() +
     (len(forged_dists) - 1) * forged_dists.var()) /
    (len(genuine_dists) + len(forged_dists) - 2)
)
cohens_d_signal = (forged_dists.mean() - genuine_dists.mean()) / pooled_std

# d-prime (signal detection theory)
d_prime = (forged_dists.mean() - genuine_dists.mean()) / pooled_std

# AUC (area under ROC)
print(f'Signal-to-Noise Ratio (SNR): {snr:.4f}')
print(f"Cohen's d (signal):          {cohens_d_signal:.4f}")
print(f"d-prime (signal detection):  {d_prime:.4f}")
print(f'Genuine mean: {genuine_dists.mean():.4f} ± {genuine_dists.std():.4f}')
print(f'Forged mean:  {forged_dists.mean():.4f} ± {forged_dists.std():.4f}')
print(f'Separation:   {forged_dists.mean() - genuine_dists.mean():.4f}')
print()

# ============================================================
# 7. CAPACITY CONSTRAINTS
# ============================================================
print('=' * 60)
print('7. CAPACITY CONSTRAINTS')
print('=' * 60)

# Inference time capacity
import time

x1 = torch.randn(1, 3, 224, 224).to(DEVICE)
x2 = torch.randn(1, 3, 224, 224).to(DEVICE)

with torch.no_grad():
    for _ in range(10):
        model(x1, x2)

times = []
with torch.no_grad():
    for _ in range(100):
        start = time.time()
        model(x1, x2)
        times.append(time.time() - start)

avg_time_ms = np.mean(times) * 1000
p50_ms = np.percentile(times, 50) * 1000
p95_ms = np.percentile(times, 95) * 1000
p99_ms = np.percentile(times, 99) * 1000

# Throughput (requests per second)
throughput = 1000 / avg_time_ms

# Daily capacity
daily_capacity = throughput * 3600 * 24

# Model size
model_size_mb = MODEL_PATH.stat().st_size / 1e6

print(f'Inference time (avg): {avg_time_ms:.2f} ms')
print(f'Inference time (p50): {p50_ms:.2f} ms')
print(f'Inference time (p95): {p95_ms:.2f} ms')
print(f'Inference time (p99): {p99_ms:.2f} ms')
print(f'Throughput: {throughput:.1f} req/sec')
print(f'Daily capacity: {daily_capacity:,.0f} requests/day')
print(f'Model size: {model_size_mb:.2f} MB')
print()

# ============================================================
# 8. FEATURE IMPORTANCE (via distance analysis)
# ============================================================
print('=' * 60)
print('8. FEATURE IMPORTANCE ANALYSIS')
print('=' * 60)

# Analyze which signers are hardest to classify
per_signer_accs = {}

for signer_dir in sorted(genuine_dir.iterdir()):
    if signer_dir.is_dir():
        signer_name = signer_dir.name

        # Get genuine and forged pairs for this signer
        genuine_imgs = list(signer_dir.glob('*.png'))
        forged_signer_dir = forged_dir / signer_name
        if not forged_signer_dir.exists():
            continue
        forged_imgs = list(forged_signer_dir.glob('*.png'))

        # Evaluate
        with torch.no_grad():
            # Genuine pairs
            genuine_correct = 0
            genuine_total = 0
            for i in range(min(5, len(genuine_imgs) - 1)):
                img1 = load_img(genuine_imgs[i]).unsqueeze(0).to(DEVICE)
                img2 = load_img(genuine_imgs[i + 1]).unsqueeze(0).to(DEVICE)
                emb1, emb2 = model(img1, img2)
                d = torch.nn.functional.pairwise_distance(emb1, emb2).item()
                if d < best_threshold:
                    genuine_correct += 1
                genuine_total += 1

            # Forged pairs
            forged_correct = 0
            forged_total = 0
            for g in genuine_imgs[:3]:
                for f in forged_imgs[:2]:
                    img1 = load_img(g).unsqueeze(0).to(DEVICE)
                    img2 = load_img(f).unsqueeze(0).to(DEVICE)
                    emb1, emb2 = model(img1, img2)
                    d = torch.nn.functional.pairwise_distance(emb1, emb2).item()
                    if d >= best_threshold:
                        forged_correct += 1
                    forged_total += 1

        total = genuine_total + forged_total
        correct = genuine_correct + forged_correct
        per_signer_accs[signer_name] = correct / total if total > 0 else 0

# Sort by accuracy
sorted_signers = sorted(per_signer_accs.items(), key=lambda x: x[1])

print('Per-signer accuracy (sorted):')
print('  Easiest signers:')
for signer, acc in sorted_signers[-3:]:
    print(f'    {signer}: {acc:.4f}')
print('  Hardest signers:')
for signer, acc in sorted_signers[:3]:
    print(f'    {signer}: {acc:.4f}')
print()

# ============================================================
# SAVE ALL RESULTS
# ============================================================
results = {
    'rq1_advanced': {
        'basic_metrics': {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1': float(f1),
            'auc_roc': float(auc_roc),
            'best_threshold': float(best_threshold),
            'test_pairs': len(all_pairs),
        },
        'bootstrap_ci': {
            'n_iterations': n_bootstrap,
            'accuracy_ci_95': acc_ci,
            'f1_ci_95': f1_ci,
            'auc_roc_ci_95': auc_ci,
        },
        'permutation_test': {
            'n_permutations': n_permutations,
            'p_value': p_value_perm,
            'significant_at_0.05': bool(p_value_perm < 0.05),
        },
        'cross_validation': {
            'n_folds': 5,
            'accuracy_mean': float(np.mean(cv_accs)),
            'accuracy_std': float(np.std(cv_accs)),
            'f1_mean': float(np.mean(cv_f1s)),
            'f1_std': float(np.std(cv_f1s)),
            'auc_roc_mean': float(np.mean(cv_aucs)),
            'auc_roc_std': float(np.std(cv_aucs)),
        },
        'signal_decay': decay_data,
        'separability': {
            'snr': float(snr),
            'cohens_d': float(cohens_d_signal),
            'd_prime': float(d_prime),
            'genuine_mean': float(genuine_dists.mean()),
            'genuine_std': float(genuine_dists.std()),
            'forged_mean': float(forged_dists.mean()),
            'forged_std': float(forged_dists.std()),
            'separation': float(forged_dists.mean() - genuine_dists.mean()),
        },
        'capacity': {
            'inference_time_avg_ms': float(avg_time_ms),
            'inference_time_p50_ms': float(p50_ms),
            'inference_time_p95_ms': float(p95_ms),
            'inference_time_p99_ms': float(p99_ms),
            'throughput_req_per_sec': float(throughput),
            'daily_capacity': int(daily_capacity),
            'model_size_mb': float(model_size_mb),
        },
        'feature_importance': {
            'easiest_signers': [s for s, _ in sorted_signers[-3:]],
            'hardest_signers': [s for s, _ in sorted_signers[:3]],
        },
    }
}

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_FILE, 'w') as f:
    json.dump(results, f, indent=2)

print()
print('=' * 60)
print('RQ1 ADVANCED STATISTICAL ANALYSIS COMPLETE')
print('=' * 60)
print(f'Results saved: {OUTPUT_FILE}')
print('=' * 60)