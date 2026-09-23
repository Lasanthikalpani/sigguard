"""Training loop for Siamese signature verification (RQ1).

SigGuard - AI-Powered Signature Forgery Detection
"""
import os
import time
import random
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from src.models.siamese import SiameseNetwork, ContrastiveLoss
from src.data.dataset import SignaturePairDataset
from src.training.config import TrainingConfig


def set_seed(seed: int):
    """Set random seeds for reproducibility."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device(device_str: str) -> torch.device:
    """Get device from config string."""
    if device_str == 'auto':
        return torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    return torch.device(device_str)


def train_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
    log_interval: int = 10,
) -> float:
    """Train for one epoch."""
    model.train()
    total_loss = 0.0

    for batch_idx, (img1, img2, labels) in enumerate(dataloader):
        img1 = img1.to(device)
        img2 = img2.to(device)
        labels = labels.to(device)

        optimizer.zero_grad()
        emb1, emb2 = model(img1, img2)
        loss = criterion(emb1, emb2, labels)
        loss.backward()
        optimizer.step()

        total_loss += loss.item()

        if (batch_idx + 1) % log_interval == 0:
            print(f'    Batch {batch_idx + 1}/{len(dataloader)} | '
                  f'Loss: {loss.item():.4f}')

    return total_loss / len(dataloader)


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """Validate model."""
    model.eval()
    total_loss = 0.0

    with torch.no_grad():
        for img1, img2, labels in dataloader:
            img1 = img1.to(device)
            img2 = img2.to(device)
            labels = labels.to(device)

            emb1, emb2 = model(img1, img2)
            loss = criterion(emb1, emb2, labels)
            total_loss += loss.item()

    return total_loss / len(dataloader)


def train(
    config: Optional[TrainingConfig] = None,
    data_dir: Optional[str] = None,
) -> dict:
    """Main training function."""
    config = config or TrainingConfig()
    data_dir = data_dir or config.data_dir

    set_seed(config.seed)
    device = get_device(config.device)
    print(f'Device: {device}')

    checkpoint_dir = Path(config.checkpoint_dir)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    print(f'\nLoading dataset from: {data_dir}')
    try:
        dataset = SignaturePairDataset(
            data_dir=data_dir,
            pairs_per_epoch=config.pairs_per_epoch,
            positive_ratio=config.positive_ratio,
        )
        print(f'  Signers found: {len(dataset.signer_ids)}')
    except ValueError as e:
        print(f'  [WARN] Dataset error: {e}')
        print('  Creating synthetic data for demo...')
        return _train_with_synthetic(config, device)

    dataloader = DataLoader(
        dataset,
        batch_size=config.batch_size,
        shuffle=True,
        num_workers=config.num_workers,
        pin_memory=False,
    )

    print(f'\nCreating model: {config.backbone} (embedding_dim={config.embedding_dim})')
    model = SiameseNetwork(
        embedding_dim=config.embedding_dim,
        backbone=config.backbone,
        pretrained=config.pretrained,
    ).to(device)

    total_params = sum(p.numel() for p in model.parameters())
    print(f'  Total parameters: {total_params:,}')

    criterion = ContrastiveLoss(margin=config.margin)
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='min',
        patience=config.scheduler_patience,
        factor=config.scheduler_factor,
    )

    print(f'\nStarting training for {config.epochs} epochs...')
    best_val_loss = float('inf')
    patience_counter = 0
    history = {'train_loss': [], 'val_loss': []}

    start_time = time.time()

    for epoch in range(1, config.epochs + 1):
        epoch_start = time.time()

        train_loss = train_epoch(
            model, dataloader, criterion, optimizer, device, config.log_interval
        )
        val_loss = validate(model, dataloader, criterion, device)
        scheduler.step(val_loss)

        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)

        epoch_time = time.time() - epoch_start
        current_lr = optimizer.param_groups[0]['lr']

        print(f'  Epoch {epoch:3d}/{config.epochs} | '
              f'Train: {train_loss:.4f} | '
              f'Val: {val_loss:.4f} | '
              f'LR: {current_lr:.2e} | '
              f'Time: {epoch_time:.1f}s')

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0

            checkpoint_path = checkpoint_dir / 'best_model.pth'
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': config.to_dict(),
            }, checkpoint_path)
            print(f'    [SAVED] Best model: {checkpoint_path}')
        else:
            patience_counter += 1

        if patience_counter >= config.early_stopping_patience:
            print(f'\n  Early stopping at epoch {epoch}')
            break

    total_time = time.time() - start_time

    print(f'\n[OK] Training complete in {total_time:.1f}s')
    print(f'  Best validation loss: {best_val_loss:.4f}')
    print(f'  Checkpoint: {checkpoint_dir / "best_model.pth"}')

    return {
        'best_val_loss': best_val_loss,
        'total_time': total_time,
        'epochs_trained': epoch,
        'history': history,
    }


def _train_with_synthetic(config: TrainingConfig, device: torch.device) -> dict:
    """Fallback: train with synthetic data."""
    import tempfile
    import cv2

    print('  Creating synthetic dataset...')
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        for signer_idx in range(5):
            signer_dir = data_dir / 'genuine' / f'signer_{signer_idx:03d}'
            signer_dir.mkdir(parents=True)

            for sig_idx in range(3):
                img = np.ones((300, 500), dtype=np.uint8) * 255
                pts = np.array([
                    [50, 150 + signer_idx * 15],
                    [200, 100 + sig_idx * 20],
                    [400, 150 + signer_idx * 10],
                ], np.int32)
                cv2.polylines(img, [pts], False, 0, 3)
                cv2.imwrite(str(signer_dir / f'sig_{sig_idx:03d}.png'), img)

        print(f'  Synthetic data: 5 signers x 3 signatures')

        dataset = SignaturePairDataset(
            data_dir=str(data_dir),
            pairs_per_epoch=config.pairs_per_epoch,
            positive_ratio=config.positive_ratio,
        )

        dataloader = DataLoader(
            dataset,
            batch_size=config.batch_size,
            shuffle=True,
            num_workers=0,
        )

        model = SiameseNetwork(
            embedding_dim=config.embedding_dim,
            backbone=config.backbone,
            pretrained=config.pretrained,
        ).to(device)

        criterion = ContrastiveLoss(margin=config.margin)
        optimizer = torch.optim.Adam(
            model.parameters(),
            lr=config.learning_rate,
        )

        demo_epochs = 5
        print(f'\n  Training for {demo_epochs} epochs (demo)...')

        for epoch in range(1, demo_epochs + 1):
            train_loss = train_epoch(
                model, dataloader, criterion, optimizer, device, log_interval=5
            )
            val_loss = validate(model, dataloader, criterion, device)
            print(f'  Epoch {epoch}/{demo_epochs} | '
                  f'Train: {train_loss:.4f} | Val: {val_loss:.4f}')

        checkpoint_dir = Path(config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / 'demo_model.pth'

        torch.save({
            'epoch': demo_epochs,
            'model_state_dict': model.state_dict(),
            'val_loss': val_loss,
            'config': config.to_dict(),
        }, checkpoint_path)

        print(f'\n[OK] Demo training complete')
        print(f'  Checkpoint: {checkpoint_path}')

        return {
            'best_val_loss': val_loss,
            'epochs_trained': demo_epochs,
            'demo': True,
        }


if __name__ == '__main__':
    config = TrainingConfig()
    config.epochs = 50               # Full training
    config.pairs_per_epoch = 500     # More pairs
    config.batch_size = 32           # Larger batch
    config.learning_rate = 5e-4      # Higher LR
    config.early_stopping_patience = 15
    config.scheduler_patience = 5
    config.scheduler_factor = 0.5

    results = train(config)
    print(f'\nResults: {results}')
