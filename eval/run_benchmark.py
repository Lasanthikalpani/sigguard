"""Evaluation harness for Siamese signature verification (RQ1).

SigGuard - AI-Powered Signature Forgery Detection
5-fold stratified cross-validation with regression testing.
"""
import time
from pathlib import Path
from typing import Optional, Dict, List

import numpy as np
import torch
from torch.utils.data import DataLoader
from sklearn.model_selection import StratifiedKFold

from src.models.siamese import SiameseNetwork, ContrastiveLoss
from src.data.dataset import SignatureTestDataset
from src.evaluation.metrics import compute_metrics
from src.training.config import TrainingConfig
from src.training.train import set_seed, get_device


class EvaluationHarness:
    """5-fold cross-validation harness for SigGuard (RQ1)."""

    def __init__(
        self,
        config: Optional[TrainingConfig] = None,
        n_folds: int = 5,
        accuracy_threshold: float = 0.92,
    ):
        self.config = config or TrainingConfig()
        self.n_folds = n_folds
        self.accuracy_threshold = accuracy_threshold
        self.results = {}

    def run(self, pairs: List, signer_ids: List[str], verbose: bool = True) -> Dict:
        """Run 5-fold cross-validation."""
        set_seed(self.config.seed)
        device = get_device(self.config.device)

        if verbose:
            print(f'Device: {device}')
            print(f'Total pairs: {len(pairs)}')
            print(f'Folds: {self.n_folds}')
            print(f'Accuracy threshold: {self.accuracy_threshold}')
            print()

        labels = np.array([p[2] for p in pairs])
        skf = StratifiedKFold(
            n_splits=self.n_folds, shuffle=True, random_state=self.config.seed
        )

        fold_metrics = []
        for fold_idx, (train_idx, test_idx) in enumerate(
            skf.split(pairs, labels), start=1
        ):
            if verbose:
                print(f'=== Fold {fold_idx}/{self.n_folds} ===')

            train_pairs = [pairs[i] for i in train_idx]
            test_pairs = [pairs[i] for i in test_idx]

            metrics = self._train_and_evaluate(train_pairs, test_pairs, device)
            fold_metrics.append(metrics)

            if verbose:
                print(f'  Accuracy: {metrics["accuracy"]:.4f}')
                print(f'  F1: {metrics["f1"]:.4f}')
                print(f'  AUC-ROC: {metrics["auc_roc"]:.4f}')
                print()

        self.results = self._aggregate(fold_metrics)
        return self.results

    def _train_and_evaluate(
        self, train_pairs: List, test_pairs: List, device: torch.device
    ) -> Dict:
        """Train on train_pairs, evaluate on test_pairs."""
        model = SiameseNetwork(
            embedding_dim=self.config.embedding_dim,
            backbone=self.config.backbone,
            pretrained=self.config.pretrained,
        ).to(device)

        criterion = ContrastiveLoss(margin=self.config.margin)
        optimizer = torch.optim.Adam(
            model.parameters(), lr=self.config.learning_rate
        )

        train_dataset = SignatureTestDataset(
            pairs=[(str(p[0]), str(p[1]), int(p[2])) for p in train_pairs],
        )
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            shuffle=True,
            num_workers=0,
        )

        model.train()
        for epoch in range(min(3, self.config.epochs)):
            for img1, img2, labels in train_loader:
                img1 = img1.to(device)
                img2 = img2.to(device)
                labels = labels.to(device)

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
            test_dataset,
            batch_size=self.config.batch_size,
            shuffle=False,
            num_workers=0,
        )

        all_labels = []
        all_preds = []
        all_probs = []
        inference_times = []

        with torch.no_grad():
            for img1, img2, labels in test_loader:
                img1 = img1.to(device)
                img2 = img2.to(device)

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
        """Aggregate metrics across folds."""
        aggregated = {}
        for key in fold_metrics[0].keys():
            values = [m[key] for m in fold_metrics]
            aggregated[key] = {
                'mean': float(np.mean(values)),
                'std': float(np.std(values)),
                'min': float(np.min(values)),
                'max': float(np.max(values)),
                'values': values,
            }
        return aggregated

    def regression_test(self) -> bool:
        """Check if accuracy meets threshold."""
        if not self.results:
            raise ValueError('Run evaluation first')

        accuracy = self.results['accuracy']['mean']
        threshold = self.accuracy_threshold

        print(f'\n=== Regression Test ===')
        print(f'Accuracy: {accuracy:.4f}')
        print(f'Threshold: {threshold}')

        if accuracy >= threshold:
            print(f'[PASS] Accuracy >= {threshold}')
            return True
        print(f'[FAIL] Accuracy < {threshold} (expected with synthetic data)')
        return False

    def print_summary(self):
        """Print summary table."""
        print('\n' + '=' * 60)
        print('Evaluation Summary')
        print('=' * 60)
        print(f'{"Metric":<20} {"Mean":>10} {"Std":>10} {"Min":>10} {"Max":>10}')
        print('-' * 60)

        for key in ['accuracy', 'precision', 'recall', 'f1', 'auc_roc']:
            if key in self.results:
                r = self.results[key]
                print(
                    f'{key:<20} {r["mean"]:>10.4f} {r["std"]:>10.4f} '
                    f'{r["min"]:>10.4f} {r["max"]:>10.4f}'
                )

        if 'inference_time' in self.results:
            r = self.results['inference_time']
            print(
                f'{"inference_time (s)":<20} {r["mean"]:>10.4f} '
                f'{r["std"]:>10.4f} {r["min"]:>10.4f} {r["max"]:>10.4f}'
            )

        print('=' * 60)


def create_synthetic_pairs(n_signers: int = 5, n_per_signer: int = 3):
    """Create synthetic signature pairs for testing."""
    import tempfile
    import cv2

    tmpdir = tempfile.mkdtemp()
    data_dir = Path(tmpdir)

    for signer_idx in range(n_signers):
        signer_dir = data_dir / 'genuine' / f'signer_{signer_idx:03d}'
        signer_dir.mkdir(parents=True)

        for sig_idx in range(n_per_signer):
            img = np.ones((300, 500), dtype=np.uint8) * 255
            pts = np.array(
                [
                    [50, 150 + signer_idx * 15],
                    [200, 100 + sig_idx * 20],
                    [400, 150 + signer_idx * 10],
                ],
                np.int32,
            )
            cv2.polylines(img, [pts], False, 0, 3)
            cv2.imwrite(str(signer_dir / f'sig_{sig_idx:03d}.png'), img)

    pairs = []
    signer_ids = []

    for signer_idx in range(n_signers):
        signer_dir = data_dir / 'genuine' / f'signer_{signer_idx:03d}'
        images = list(signer_dir.glob('*.png'))

        for i in range(len(images)):
            for j in range(i + 1, len(images)):
                pairs.append((images[i], images[j], 0))
                signer_ids.append(f'signer_{signer_idx:03d}')

        for other_idx in range(n_signers):
            if other_idx == signer_idx:
                continue
            other_dir = data_dir / 'genuine' / f'signer_{other_idx:03d}'
            other_images = list(other_dir.glob('*.png'))
            pairs.append((images[0], other_images[0], 1))
            signer_ids.append(f'signer_{signer_idx:03d}')

    return pairs, signer_ids, data_dir


if __name__ == '__main__':
    print('=' * 60)
    print('SigGuard - RQ1 Evaluation Harness')
    print('=' * 60)

    print('\nCreating synthetic data...')
    pairs, signer_ids, data_dir = create_synthetic_pairs(n_signers=5)
    print(f'  Pairs: {len(pairs)}')
    print(f'  Signers: {len(set(signer_ids))}')

    config = TrainingConfig()
    config.epochs = 3

    harness = EvaluationHarness(config=config, n_folds=5, accuracy_threshold=0.92)

    results = harness.run(pairs, signer_ids, verbose=True)
    harness.print_summary()
    harness.regression_test()

    print('\n[OK] Evaluation harness complete')
