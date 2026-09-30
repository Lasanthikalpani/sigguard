"""RQ1 Data Pipeline v2 - Uses existing data/splits_v2."""
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List

import pandas as pd


class DataPipelineV2:
    """Simplified data pipeline using existing data/splits_v2."""

    def __init__(
        self,
        source_dir: str = 'data/splits_v2',
        metadata_dir: str = 'data/metadata',
    ):
        self.source_dir = Path(source_dir)
        self.metadata_dir = Path(metadata_dir)
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def ingest(self) -> List[Dict]:
        """Ingest records from data/splits_v2."""
        records = []

        for split in ['train', 'val', 'test']:
            split_dir = self.source_dir / split
            if not split_dir.exists():
                print(f'  [SKIP] {split} not found')
                continue

            for cls in ['genuine', 'forged']:
                cls_dir = split_dir / cls
                if not cls_dir.exists():
                    continue

                for signer_dir in sorted(cls_dir.iterdir()):
                    if not signer_dir.is_dir():
                        continue

                    for img_path in sorted(signer_dir.glob('*.png')):
                        records.append({
                            'file_path': str(img_path),
                            'filename': img_path.name,
                            'label': 0 if cls == 'genuine' else 1,
                            'class': cls,
                            'signer_id': signer_dir.name,
                            'script': 'english',
                            'split': split,
                            'file_hash': self._file_hash(img_path),
                            'file_size': img_path.stat().st_size,
                            'ingested_at': datetime.now().isoformat(),
                        })

        print(f'[OK] Ingested {len(records)} records')
        genuine = sum(1 for r in records if r['label'] == 0)
        forged = sum(1 for r in records if r['label'] == 1)
        signers = len(set(r['signer_id'] for r in records))
        print(f'     Genuine: {genuine}, Forged: {forged}')
        print(f'     Signers: {signers}')

        for split in ['train', 'val', 'test']:
            split_records = [r for r in records if r['split'] == split]
            if split_records:
                split_signers = len(set(r['signer_id'] for r in split_records))
                print(f'     {split}: {len(split_records)} records, {split_signers} signers')

        return records

    def save_metadata(self, records: List[Dict]):
        """Save metadata to CSV and JSON."""
        df = pd.DataFrame(records)
        csv_path = self.metadata_dir / 'dataset.csv'
        df.to_csv(csv_path, index=False)
        print(f'[OK] Metadata CSV: {csv_path}')

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
        hashes = sorted(r['file_hash'] for r in records)
        combined = ''.join(hashes).encode()
        return hashlib.sha256(combined).hexdigest()[:16]

    def _file_hash(self, path: Path) -> str:
        return hashlib.md5(path.read_bytes()).hexdigest()

    def run(self):
        print('=' * 60)
        print('SigGuard Data Pipeline v2')
        print('=' * 60)

        print('\n[1/2] Ingesting data from splits_v2...')
        records = self.ingest()

        print('\n[2/2] Saving metadata...')
        self.save_metadata(records)

        print('\n' + '=' * 60)
        print('Pipeline complete!')
        print('=' * 60)

        return records


if __name__ == '__main__':
    pipeline = DataPipelineV2()
    records = pipeline.run()