"""Evaluation metrics for SigGuard (RQ1)."""
from typing import Dict
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    confusion_matrix,
)


def compute_metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    probabilities: np.ndarray,
) -> Dict[str, float]:
    """Compute all metrics for signature verification."""
    return {
        'accuracy': float(accuracy_score(labels, predictions)),
        'precision': float(precision_score(labels, predictions, zero_division=0)),
        'recall': float(recall_score(labels, predictions, zero_division=0)),
        'f1': float(f1_score(labels, predictions, zero_division=0)),
        'auc_roc': float(roc_auc_score(labels, probabilities)),
    }


def compute_confusion_matrix(
    labels: np.ndarray,
    predictions: np.ndarray,
) -> Dict[str, int]:
    """Compute confusion matrix components."""
    tn, fp, fn, tp = confusion_matrix(labels, predictions).ravel()
    return {
        'true_negative': int(tn),
        'false_positive': int(fp),
        'false_negative': int(fn),
        'true_positive': int(tp),
    }


def compute_far_frr(
    labels: np.ndarray,
    predictions: np.ndarray,
) -> Dict[str, float]:
    """Compute FAR, FRR, EER."""
    cm = compute_confusion_matrix(labels, predictions)
    fp = cm['false_positive']
    tn = cm['true_negative']
    fn = cm['false_negative']
    tp = cm['true_positive']

    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    frr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        'far': float(far),
        'frr': float(frr),
        'eer': float((far + frr) / 2),
    }


if __name__ == '__main__':
    np.random.seed(42)
    n = 100
    labels = np.random.randint(0, 2, n)
    probabilities = np.random.rand(n)
    predictions = (probabilities > 0.5).astype(int)

    metrics = compute_metrics(labels, predictions, probabilities)
    print('Metrics:')
    for k, v in metrics.items():
        print(f'  {k}: {v:.4f}')

    cm = compute_confusion_matrix(labels, predictions)
    print('Confusion matrix:')
    for k, v in cm.items():
        print(f'  {k}: {v}')

    far_frr = compute_far_frr(labels, predictions)
    print('FAR/FRR:')
    for k, v in far_frr.items():
        print(f'  {k}: {v:.4f}')

    print('[OK] Metrics work')
