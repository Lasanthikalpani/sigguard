"""Production-grade evaluation harness for RQ1 (MindHive-style)."""
import time
import json
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

            metrics = self._train_and_evaluate(train_pairs, test_pairs, device)
            fold_metrics.append(metrics)

            if verbose:
                print(f'  Accuracy: {metrics["accuracy"]:.4f}')
                print(f'  F1: {metrics["f1"]:.4f}')
                print(f'  AUC-ROC: {metrics["auc_roc"]:.4f}')

        self.results = self._aggregate(fold_metrics)
        return self.results

    def _train_and_evaluate(
        self, train_pairs: List, test_pairs: List, device
    ) -> Dict:
        """Train + evaluate one fold."""
        model = SiameseNetwork(
            embedding_dim=self.config.embedding_dim,
            backbone=self.config.backbone,
            pretrained=self.config.pretrained,
        ).to(device)

        criterion = ContrastiveLoss(margin=self.config.margin)
        optimizer = torch.optim.Adam(model.parameters(), lr=self.config.learning_rate)

        train_dataset = SignatureTestDataset(
            pairs=[(str(p[0]), str(p[1]), int(p[2])) for p in train_pairs],
        )
        train_loader = DataLoader(
            train_dataset, batch_size=self.config.batch_size,
            shuffle=True, num_workers=0,
        )

        model.train()
        for _ in range(min(3, self.config.epochs)):
            for img1, img2, labels in train_loader:
                img1, img2, labels = img1.to(device), img2.to(device), labels.to(device)
                optimizer.zero_grad()
                emb1, emb2 = model(img1, img2)
                loss = criterion(emb1, emb2, labels)
                loss.backward()
                optimizer.step()

        model.eval()
        test_dataset = SignatureTestDataset(
            pairs=[(str(p[0]), str(p[1]), int(p[2])) for p in test_pairs],
        )
        test_loader = DataLoader(
            test_dataset, batch_size=self.config.batch_size,
            shuffle=False, num_workers=0,
        )

        all_labels, all_preds, all_probs = [], [], []
        inference_times = []

        with torch.no_grad():
            for img1, img2, labels in test_loader:
                img1, img2 = img1.to(device), img2.to(device)
                start = time.time()
                emb1, emb2 = model(img1, img2)
                distance = torch.nn.functional.pairwise_distance(emb1, emb2)
                inference_times.append((time.time() - start) / len(labels))

                prob = torch.clamp(1.0 - distance / 2.0, 0.0, 1.0)
                pred = (prob < 0.5).float()

                all_labels.extend(labels.numpy().tolist())
                all_preds.extend(pred.cpu().numpy().tolist())
                all_probs.extend(prob.cpu().numpy().tolist())

        metrics = compute_metrics(
            np.array(all_labels), np.array(all_preds), np.array(all_probs)
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