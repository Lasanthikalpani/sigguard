"""RQ1 Data Pipeline - Production Grade.

End-to-end data pipeline:
- Ingestion: Load raw signature data
- Cleaning: Preprocess images
- Storage: PostgreSQL + File system
- Versioning: DVC-style hashing
"""
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

import cv2
import numpy as np
import pandas as pd


class DataPipeline:
    """End-to-end data pipeline for SigGuard RQ1."""

    def __init__(
        self,
        raw_dir: str = 'data/raw',
        processed_dir: str = 'data/processed',
        metadata_dir: str = 'data/metadata',
    ):
        self.raw_dir = Path(raw_dir)
        self.processed_dir = Path(processed_dir)
        self.metadata_dir = Path(metadata_dir)

        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

        self.records = []

    # ============ INGESTION ============
    def ingest(self, source_dir: Optional[str] = None) -> List[Dict]:
        """Ingest raw data from source directory.

        Args:
            source_dir: Optional source directory override.

        Returns:
            List of records with metadata.
        """
        source = Path(source_dir) if source_dir else self.raw_dir
        records = []

        for cls in ['genuine', 'forged']:
            cls_dir = source / cls / 'english'
            if not cls_dir.exists():
                # Try without 'english' subdirectory
                cls_dir = source / cls
                if not cls_dir.exists():
                    continue

            for signer_dir in sorted(cls_dir.iterdir()):
                if not signer_dir.is_dir():
                    continue

                signer_id = signer_dir.name

                for img_path in sorted(signer_dir.glob('*.png')):
                    record = {
                        'file_path': str(img_path),
                        'filename': img_path.name,
                        'label': 0 if cls == 'genuine' else 1,
                        'class': cls,
                        'signer_id': signer_id,
                        'script': 'english',
                        'file_hash': self._file_hash(img_path),
                        'file_size': img_path.stat().st_size,
                        'ingested_at': datetime.now().isoformat(),
                    }
                    records.append(record)

        self.records = records
        print(f'[OK] Ingested {len(records)} records')

        # Summary
        genuine_count = sum(1 for r in records if r['label'] == 0)
        forged_count = sum(1 for r in records if r['label'] == 1)
        signers = set(r['signer_id'] for r in records)
        print(f'     Genuine: {genuine_count}, Forged: {forged_count}')
        print(f'     Signers: {len(signers)}')

        return records

    # ============ CLEANING ============
    def clean(self, records: Optional[List[Dict]] = None) -> List[Dict]:
        """Clean and preprocess records.

        Args:
            records: Optional records list override.

        Returns:
            List of cleaned records.
        """
        records = records or self.records
        cleaned = []

        for record in records:
            img = cv2.imread(record['file_path'], cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue

            # Quality check
            if img.shape[0] < 50 or img.shape[1] < 50:
                continue

            # Preprocess
            processed = self._preprocess(img)

            # Save processed
            output_path = self._save_processed(processed, record)

            record['processed_path'] = str(output_path)
            record['original_shape'] = list(img.shape)
            record['processed_shape'] = list(processed.shape)
            record['cleaned_at'] = datetime.now().isoformat()

            cleaned.append(record)

        self.records = cleaned
        print(f'[OK] Cleaned {len(cleaned)} records')

        return cleaned

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """Preprocess signature image."""
        # 1. Denoise (Non-Local Means)
        img = cv2.fastNlMeansDenoising(img, h=10)

        # 2. Binarize (Otsu)
        _, img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # 3. Deskew
        coords = np.column_stack(np.where(img > 0))
        if len(coords) > 10:
            angle = cv2.minAreaRect(coords)[-1]
            if angle < -45:
                angle = -(90 + angle)
            else:
                angle = -angle

            if abs(angle) > 0.5:
                h, w = img.shape
                M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
                img = cv2.warpAffine(
                    img, M, (w, h),
                    flags=cv2.INTER_CUBIC,
                    borderMode=cv2.BORDER_REPLICATE,
                )

        # 4. Resize
        img = cv2.resize(img, (224, 224))

        return img

    def _save_processed(self, img: np.ndarray, record: Dict) -> Path:
        """Save processed image."""
        output_dir = (
            self.processed_dir
            / record['class']
            / record['signer_id']
        )
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = output_dir / record['filename']
        cv2.imwrite(str(output_path), img)

        return output_path

    # ============ STORAGE ============
    def save_metadata(self, records: Optional[List[Dict]] = None):
        """Save metadata to CSV and JSON."""
        records = records or self.records

        # CSV
        df = pd.DataFrame(records)
        csv_path = self.metadata_dir / 'dataset.csv'
        df.to_csv(csv_path, index=False)
        print(f'[OK] Metadata CSV: {csv_path}')

        # JSON (with versioning)
        json_path = self.metadata_dir / 'dataset.json'
        with open(json_path, 'w') as f:
            json.dump({
                'version': self._compute_version(records),
                'created_at': datetime.now().isoformat(),
                'total_records': len(records),
                'records': records,
            }, f, indent=2)
        print(f'[OK] Metadata JSON: {json_path}')

    def _compute_version(self, records: List[Dict]) -> str:
        """Compute dataset version hash."""
        hashes = sorted(r['file_hash'] for r in records)
        combined = ''.join(hashes).encode()
        return hashlib.sha256(combined).hexdigest()[:16]

    def _file_hash(self, path: Path) -> str:
        """Compute file hash (MD5)."""
        return hashlib.md5(path.read_bytes()).hexdigest()

    # ============ SPLIT ============
    def create_signer_split(
        self,
        output_dir: str = 'data/splits_v2',
        train_ratio: float = 0.70,
        val_ratio: float = 0.15,
        seed: int = 42,
    ) -> Dict:
        """Create signer-based split.

        Args:
            output_dir: Output directory for split.
            train_ratio: Training ratio.
            val_ratio: Validation ratio.
            seed: Random seed.

        Returns:
            Split summary.
        """
        import shutil
        import random

        records = self.records
        output = Path(output_dir)

        # Find common signers
        genuine_signers = set(
            r['signer_id'] for r in records if r['label'] == 0
        )
        forged_signers = set(
            r['signer_id'] for r in records if r['label'] == 1
        )
        common = sorted(genuine_signers & forged_signers)

        if len(common) < 2:
            raise ValueError(f'Need >= 2 common signers, found {len(common)}')

        # Shuffle
        random.seed(seed)
        random.shuffle(common)

        n = len(common)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            'train': common[:n_train],
            'val': common[n_train:n_train + n_val],
            'test': common[n_train + n_val:],
        }

        # Clean output
        if output.exists():
            shutil.rmtree(output)

        # Copy
        for split_name, signer_list in splits.items():
            for cls in ['genuine', 'forged']:
                (output / split_name / cls).mkdir(parents=True, exist_ok=True)

            for signer in signer_list:
                for cls in ['genuine', 'forged']:
                    src = self.processed_dir / cls / signer
                    if src.exists():
                        dst = output / split_name / cls / signer
                        shutil.copytree(src, dst, dirs_exist_ok=True)

        # Summary
        summary = {}
        for split_name, signer_list in splits.items():
            genuine_count = len(list((output / split_name / 'genuine').rglob('*.png')))
            forged_count = len(list((output / split_name / 'forged').rglob('*.png')))

            summary[split_name] = {
                'signers': len(signer_list),
                'genuine': genuine_count,
                'forged': forged_count,
                'total': genuine_count + forged_count,
            }

        print(f'[OK] Signer-based split created: {output_dir}')
        for name, data in summary.items():
            print(f'     {name}: {data["signers"]} signers, {data["total"]} images')

        return summary

    # ============ FULL PIPELINE ============
    def run(self, source_dir: Optional[str] = None) -> Dict:
        """Run full pipeline."""
        print('=' * 60)
        print('SigGuard Data Pipeline')
        print('=' * 60)

        print('\n[1/4] Ingesting data...')
        self.ingest(source_dir)

        print('\n[2/4] Cleaning data...')
        self.clean()

        print('\n[3/4] Saving metadata...')
        self.save_metadata()

        print('\n[4/4] Creating signer-based split...')
        summary = self.create_signer_split()

        print('\n' + '=' * 60)
        print('Pipeline complete!')
        print('=' * 60)

        return summary


if __name__ == '__main__':
    pipeline = DataPipeline()
    summary = pipeline.run()
    print(json.dumps(summary, indent=2))