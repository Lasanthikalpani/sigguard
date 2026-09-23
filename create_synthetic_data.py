"""Create synthetic signature data for testing."""
import numpy as np
import cv2
from pathlib import Path


def create_synthetic_data(n_signers: int = 5, n_per_signer: int = 3):
    """Create synthetic signature dataset."""
    data_dir = Path('data')

    for signer_idx in range(n_signers):
        signer_id = f'signer_{signer_idx:03d}'

        # Genuine signatures (3 scripts)
        for script in ['sinhala', 'tamil', 'english']:
            signer_dir = data_dir / 'genuine' / script / signer_id
            signer_dir.mkdir(parents=True, exist_ok=True)

            for sig_idx in range(n_per_signer):
                img = np.ones((300, 500), dtype=np.uint8) * 255
                pts = np.array([
                    [50, 150 + signer_idx * 15],
                    [200, 100 + sig_idx * 20],
                    [400, 150 + signer_idx * 10],
                ], np.int32)
                cv2.polylines(img, [pts], False, 0, 3)
                cv2.imwrite(
                    str(signer_dir / f'sig_{sig_idx:03d}.png'),
                    img
                )

        # Forged signatures
        for script in ['sinhala', 'tamil', 'english']:
            signer_dir = data_dir / 'forged' / script / signer_id
            signer_dir.mkdir(parents=True, exist_ok=True)

            for sig_idx in range(n_per_signer):
                img = np.ones((300, 500), dtype=np.uint8) * 255
                pts = np.array([
                    [50, 100 + signer_idx * 20],
                    [250, 80 + sig_idx * 30],
                    [450, 120 + signer_idx * 5],
                ], np.int32)
                cv2.polylines(img, [pts], False, 0, 3)
                cv2.imwrite(
                    str(signer_dir / f'forged_{sig_idx:03d}.png'),
                    img
                )

    print(f'OK Created {n_signers} signers x {n_per_signer} signatures')
    print(f'   Genuine: data/genuine/{{sinhala,tamil,english}}/')
    print(f'   Forged: data/forged/{{sinhala,tamil,english}}/')


if __name__ == '__main__':
    create_synthetic_data(n_signers=5, n_per_signer=3)