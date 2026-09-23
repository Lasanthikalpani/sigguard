"""Training configuration for SigGuard (RQ1)."""
from dataclasses import dataclass


@dataclass
class TrainingConfig:
    """Training configuration."""

    # Model
    backbone: str = 'resnet18'
    embedding_dim: int = 128
    pretrained: bool = True

    # Loss
    loss_type: str = 'contrastive'
    margin: float = 1.0

    # Training
    epochs: int = 50
    batch_size: int = 16
    learning_rate: float = 1e-4
    weight_decay: float = 1e-5

    # Data
    data_dir: str = 'data'
    pairs_per_epoch: int = 1000
    positive_ratio: float = 0.5
    num_workers: int = 0

    # Validation
    val_split: float = 0.15
    test_split: float = 0.15
    early_stopping_patience: int = 10
    scheduler_patience: int = 5
    scheduler_factor: float = 0.5

    # Checkpointing
    checkpoint_dir: str = 'models/checkpoints'
    save_best_only: bool = True

    # Logging
    log_interval: int = 10
    experiment_name: str = 'sigguard_rq1'
    seed: int = 42

    # Device
    device: str = 'auto'

    def to_dict(self) -> dict:
        """Convert to dictionary for MLflow/DB logging."""
        return {
            'backbone': self.backbone,
            'embedding_dim': self.embedding_dim,
            'loss_type': self.loss_type,
            'margin': self.margin,
            'epochs': self.epochs,
            'batch_size': self.batch_size,
            'learning_rate': self.learning_rate,
            'weight_decay': self.weight_decay,
            'pairs_per_epoch': self.pairs_per_epoch,
            'positive_ratio': self.positive_ratio,
        }


if __name__ == '__main__':
    config = TrainingConfig()
    print('Default config:')
    for key, value in config.to_dict().items():
        print(f'  {key}: {value}')
