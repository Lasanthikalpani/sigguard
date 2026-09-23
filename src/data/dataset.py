"""PyTorch Dataset for Siamese signature verification (RQ1).

SigGuard - AI-Powered Signature Forgery Detection
"""
import random
from pathlib import Path
from typing import Optional, Tuple, List

import numpy as np
import torch
from torch.utils.data import Dataset

from src.data.preprocess import SignaturePreprocessor


class SignaturePairDataset(Dataset):
    """Dataset that generates pairs of signatures for Siamese training.

    For each sample, returns (img1, img2, label) where:
        label = 0 if same signer (genuine pair)
        label = 1 if different signer (forged pair)

    Args:
        data_dir: Root directory with structure:
            data_dir/
                genuine/
                    signer_001/
                        sig_001.png
                        sig_002.png
                forged/
                    signer_001/
                        forged_001.png
        preprocessor: SignaturePreprocessor instance.
        pairs_per_epoch: Number of pairs per epoch.
        positive_ratio: Ratio of positive pairs (same signer).
    """

    def __init__(
        self,
        data_dir: str,
        preprocessor: Optional[SignaturePreprocessor] = None,
        pairs_per_epoch: int = 1000,
        positive_ratio: float = 0.5,
    ):
        self.data_dir = Path(data_dir)
        self.preprocessor = preprocessor or SignaturePreprocessor()
        self.pairs_per_epoch = pairs_per_epoch
        self.positive_ratio = positive_ratio

        # Index all signatures by signer
        self.genuine_by_signer = self._index_signatures('genuine')
        self.forged_by_signer = self._index_signatures('forged')

        self.signer_ids = list(self.genuine_by_signer.keys())

        if len(self.signer_ids) < 2:
            raise ValueError(
                f'Need at least 2 signers, found {len(self.signer_ids)}'
            )

    def _index_signatures(self, subdir: str) -> dict:
        """Index signatures by signer ID."""
        result = {}
        root = self.data_dir / subdir

        if not root.exists():
            return result

        for signer_dir in root.iterdir():
            if not signer_dir.is_dir():
                continue

            signer_id = signer_dir.name
            images = list(signer_dir.glob('*.png')) + \
                     list(signer_dir.glob('*.jpg')) + \
                     list(signer_dir.glob('*.jpeg'))

            if images:
                result[signer_id] = images

        return result

    def __len__(self) -> int:
        return self.pairs_per_epoch

    def _load_image(self, path: Path) -> torch.Tensor:
        """Load and preprocess an image."""
        processed = self.preprocessor(path)
        # (H, W) -> (1, H, W)
        tensor = torch.from_numpy(processed).unsqueeze(0)
        # (1, H, W) -> (3, H, W) for ResNet
        tensor = tensor.repeat(3, 1, 1)
        return tensor

    def _sample_positive_pair(self) -> Tuple[Path, Path, int]:
        """Sample a genuine pair (same signer)."""
        signer = random.choice(self.signer_ids)
        images = self.genuine_by_signer[signer]

        if len(images) < 2:
            img = random.choice(images)
            return img, img, 0

        img1, img2 = random.sample(images, 2)
        return img1, img2, 0

    def _sample_negative_pair(self) -> Tuple[Path, Path, int]:
        """Sample a forged pair (different signers)."""
        signer1, signer2 = random.sample(self.signer_ids, 2)
        img1 = random.choice(self.genuine_by_signer[signer1])
        img2 = random.choice(self.genuine_by_signer[signer2])
        return img1, img2, 1

    def __getitem__(self, idx: int):
        """Get a pair of signatures."""
        if random.random() < self.positive_ratio:
            img1_path, img2_path, label = self._sample_positive_pair()
        else:
            img1_path, img2_path, label = self._sample_negative_pair()

        img1 = self._load_image(img1_path)
        img2 = self._load_image(img2_path)
        label_tensor = torch.tensor(label, dtype=torch.float32)

        return img1, img2, label_tensor


class SignatureTestDataset(Dataset):
    """Dataset for testing: fixed pairs.

    Args:
        pairs: List of (img1_path, img2_path, label) tuples.
        preprocessor: SignaturePreprocessor instance.
    """

    def __init__(
        self,
        pairs: List[Tuple[str, str, int]],
        preprocessor: Optional[SignaturePreprocessor] = None,
    ):
        self.pairs = pairs
        self.preprocessor = preprocessor or SignaturePreprocessor()

    def __len__(self) -> int:
        return len(self.pairs)

    def __getitem__(self, idx: int):
        img1_path, img2_path, label = self.pairs[idx]

        img1 = self._load_image(img1_path)
        img2 = self._load_image(img2_path)
        label_tensor = torch.tensor(label, dtype=torch.float32)

        return img1, img2, label_tensor

    def _load_image(self, path: str) -> torch.Tensor:
        processed = self.preprocessor(path)
        tensor = torch.from_numpy(processed).unsqueeze(0)
        tensor = tensor.repeat(3, 1, 1)
        return tensor


if __name__ == '__main__':
    # Test with synthetic data
    import tempfile
    import cv2

    print('Creating synthetic test data...')
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)

        # Create 3 signers with genuine signatures
        for signer_idx in range(3):
            signer_dir = data_dir / 'genuine' / f'signer_{signer_idx:03d}'
            signer_dir.mkdir(parents=True)

            for sig_idx in range(3):
                img = np.ones((300, 500), dtype=np.uint8) * 255
                pts = np.array([
                    [50, 150 + signer_idx * 10],
                    [200, 100 + sig_idx * 10],
                    [400, 150 + signer_idx * 5],
                ], np.int32)
                cv2.polylines(img, [pts], False, 0, 3)
                cv2.imwrite(str(signer_dir / f'sig_{sig_idx:03d}.png'), img)

        print(f'Created data in {data_dir}')

        # Test dataset
        dataset = SignaturePairDataset(
            data_dir=str(data_dir),
            pairs_per_epoch=10,
        )

        print(f'Dataset length: {len(dataset)}')

        img1, img2, label = dataset[0]
        print(f'img1 shape: {img1.shape}')
        print(f'img2 shape: {img2.shape}')
        print(f'label: {label.item()}')
        print('[OK] Dataset works')
