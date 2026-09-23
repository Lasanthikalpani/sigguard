"""Ablation study for RQ1 (MindHive-style trade-off analysis)."""
from itertools import product
import pandas as pd


class AblationStudy:
    """Ablation study on Siamese CNN components."""

    def __init__(self):
        self.configs = {
            'loss': ['contrastive', 'triplet'],
            'embedding_dim': [64, 128, 256],
            'backbone': ['resnet18', 'resnet50', 'mobilenet'],
            'augmentation': [True, False],
        }

    def run(self, train_fn, pairs, signer_ids):
        """Run full ablation grid."""
        results = []

        # Select subset for speed
        configs_to_test = [
            {'loss': 'contrastive', 'embedding_dim': 128, 'backbone': 'resnet18', 'augmentation': True},
            {'loss': 'contrastive', 'embedding_dim': 64, 'backbone': 'resnet18', 'augmentation': True},
            {'loss': 'contrastive', 'embedding_dim': 256, 'backbone': 'resnet18', 'augmentation': True},
            {'loss': 'triplet', 'embedding_dim': 128, 'backbone': 'resnet18', 'augmentation': True},
            {'loss': 'contrastive', 'embedding_dim': 128, 'backbone': 'resnet50', 'augmentation': True},
            {'loss': 'contrastive', 'embedding_dim': 128, 'backbone': 'mobilenet', 'augmentation': True},
            {'loss': 'contrastive', 'embedding_dim': 128, 'backbone': 'resnet18', 'augmentation': False},
        ]

        for cfg in configs_to_test:
            print(f'\nTesting: {cfg}')
            metrics = train_fn(cfg, pairs, signer_ids)
            results.append({
                **cfg,
                'accuracy': metrics['accuracy']['mean'],
                'f1': metrics['f1']['mean'],
            })

        return pd.DataFrame(results)