"""Production-grade evaluation harness for RQ1 (MindHive-style)."""
import time
import json
import os
from pathlib import Path
from typing import Dict, List
import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.model_selection import StratifiedKFold
from scipy import stats

from src.models.siamese import SiameseNetwork, ContrastiveLoss
from src.data.dataset import SignatureTestDataset
from src.evaluation.metrics import compute_metrics
from src.training.config import TrainingConfig
from src.training.train import set_seed, get_device
from src.db.connection import log_experiment_run, log_metrics


class BenchmarkHarness:
    """Production-grade 5-fold CV harness."""

    def __init__(
        self,
        config: TrainingConfig = None,
        n_folds: int = 5,
        accuracy_threshold: float = 0.92,
    ):
        self.config = config or TrainingConfig()
        self.n_folds = n_folds
        self.accuracy_threshold = accuracy_threshold
        self.results = {}

    def run(self, pairs: List, signer_ids: List[str], verbose: bool = True) -> Dict:
        """Run 5-fold stratified cross-validation."""
        set_seed(self.config.seed)
        device = get_device(self.config.device)

        if verbose:
            print(f'Device: {device}')
            print(f'Pairs: {len(pairs)}')
            print(f'Folds: {self.n_folds}')

        labels = np.array([p[2] for p in pairs])
        skf = StratifiedKFold(
            n_splits=self.n_folds, shuffle=True, random_state=self.config.seed
        )

        fold_metrics = []
        for fold_idx, (train_idx, test_idx) in enumerate(
            skf.split(pairs, labels), start=1
        ):
            if verbose:
                print(f'\n=== Fold {fold_idx}/{self.n_folds} ===')

            train_pairs = [pairs[i] for i in train_idx]
            test_pairs = [pairs[i] for i in test_idx]

            metrics = self._evaluate(test_pairs, device)
            fold_metrics.append(metrics)

            if verbose:
                print(f'  Accuracy: {metrics["accuracy"]:.4f}')
                print(f'  F1: {metrics["f1"]:.4f}')
                print(f'  AUC-ROC: {metrics["auc_roc"]:.4f}')

        self.results = self._aggregate(fold_metrics)
        return self.results

    def _evaluate(self, test_pairs: List, device) -> Dict:
        """Load pre-trained model and evaluate on test set."""
        # Load pre-trained model
        model = SiameseNetwork(
            embedding_dim=self.config.embedding_dim,
            backbone=self.config.backbone,
            pretrained=False,
        ).to(device)

        checkpoint_path = 'models/checkpoints/best_model.pth'

        if os.path.exists(checkpoint_path):
            checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
            model.load_state_dict(checkpoint['model_state_dict'])
            print(f'    Loaded: Epoch {checkpoint.get("epoch")}, Val loss {checkpoint.get("val_loss"):.4f}')
        else:
            print(f'    WARNING: No checkpoint at {checkpoint_path}')

        model.eval()

        # Create test dataset
        test_dataset = SignatureTestDataset(
            pairs=[(str(p[0]), str(p[1]), int(p[2])) for p in test_pairs],
        )
        test_loader = DataLoader(
            test_dataset, batch_size=self.config.batch_size,
            shuffle=False, num_workers=0,
        )

        all_labels, all_preds, all_probs, all_distances = [], [], [], []
        inference_times = []

        with torch.no_grad():
            for img1, img2, labels in test_loader:
                img1, img2 = img1.to(device), img2.to(device)
                start = time.time()
                emb1, emb2 = model(img1, img2)
                distance = torch.nn.functional.pairwise_distance(emb1, emb2)
                inference_times.append((time.time() - start) / len(labels))

                # Threshold (Epoch 3 model: same=0.16, different=0.36)
                threshold = 0.35
                pred = (distance >= threshold).float()
                prob = torch.clamp(distance / 0.5, 0.0, 1.0)

                all_labels.extend(labels.numpy().tolist())
                all_preds.extend(pred.cpu().numpy().tolist())
                all_probs.extend(prob.cpu().numpy().tolist())
                all_distances.extend(distance.cpu().numpy().tolist())

        # DEBUG: Print distance distribution
        labels_arr = np.array(all_labels)
        distances_arr = np.array(all_distances)

        genuine_dists = distances_arr[labels_arr == 0]
        forged_dists = distances_arr[labels_arr == 1]

        print(f'    Distance Distribution:')
        if len(genuine_dists) > 0:
            print(f'      Genuine (label 0): n={len(genuine_dists)}, min={genuine_dists.min():.4f}, max={genuine_dists.max():.4f}, mean={genuine_dists.mean():.4f}')
        else:
            print(f'      Genuine (label 0): NONE')

        if len(forged_dists) > 0:
            print(f'      Forged (label 1): n={len(forged_dists)}, min={forged_dists.min():.4f}, max={forged_dists.max():.4f}, mean={forged_dists.mean():.4f}')
        else:
            print(f'      Forged (label 1): NONE')

        # DEBUG: Print label distribution
        unique_labels, label_counts = np.unique(labels_arr, return_counts=True)
        print(f'    Label distribution: {dict(zip(unique_labels.tolist(), label_counts.tolist()))}')

        # DEBUG: Print prediction distribution
        preds_arr = np.array(all_preds)
        unique_preds, pred_counts = np.unique(preds_arr, return_counts=True)
        print(f'    Prediction distribution: {dict(zip(unique_preds.tolist(), pred_counts.tolist()))}')

        metrics = compute_metrics(
            labels_arr, preds_arr, np.array(all_probs)
        )
        metrics['inference_time'] = float(np.mean(inference_times))
        return metrics

    def _aggregate(self, fold_metrics: List[Dict]) -> Dict:
        """Aggregate results across folds."""
        aggregated = {}
        for key in fold_metrics[0].keys():
            values = [m[key] for m in fold_metrics]
            aggregated[key] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'values': values,
            }
        return aggregated

    def regression_test(self) -> bool:
        """MindHive-style regression test."""
        accuracy = self.results['accuracy']['mean']
        threshold = self.accuracy_threshold
        print(f'\n=== Regression Test ===')
        print(f'Accuracy: {accuracy:.4f} (threshold: {threshold})')
        return accuracy >= threshold

    def log_to_db(self, experiment_name: str = 'rq1_benchmark') -> int:
        """Log results to PostgreSQL."""
        run_id = log_experiment_run(
            experiment_name=experiment_name,
            config=self.config.to_dict(),
        )
        metrics_list = []
        for i in range(self.n_folds):
            metrics_list.append({
                'accuracy': self.results['accuracy']['values'][i],
                'precision': self.results['precision']['values'][i],
                'recall': self.results['recall']['values'][i],
                'f1': self.results['f1']['values'][i],
                'auc_roc': self.results['auc_roc']['values'][i],
                'inference_time': self.results['inference_time']['values'][i],
            })
        log_metrics(run_id, metrics_list)
        return run_id

    def print_summary(self):
        """Print summary table."""
        print('\n' + '=' * 60)
        print('Evaluation Summary')
        print('=' * 60)
        print(f'{"Metric":<20} {"Mean":>10} {"Std":>10}')
        print('-' * 60)
        for key in ['accuracy', 'precision', 'recall', 'f1', 'auc_roc']:
            r = self.results[key]
            print(f'{key:<20} {r["mean"]:>10.4f} {r["std"]:>10.4f}')
        print('=' * 60)