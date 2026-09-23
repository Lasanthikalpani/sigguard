"""Data loader for SigGuard — loads real signature data (RQ1)."""
import hashlib
from pathlib import Path
from typing import List

from sqlalchemy import text

from src.db.connection import get_session


class SignatureDataLoader:
    """Load signature data into PostgreSQL."""

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)

    def hash_file(self, file_path: Path) -> str:
        """SHA-256 hash of file (anonymization)."""
        return hashlib.sha256(file_path.read_bytes()).hexdigest()[:16]

    def scan_directory(self, subdir: str) -> List[dict]:
        """Scan genuine/forged directory for signatures."""
        results = []
        root = self.data_dir / subdir

        if not root.exists():
            return results

        for script_dir in root.iterdir():
            if not script_dir.is_dir():
                continue
            script = script_dir.name

            for signer_dir in script_dir.iterdir():
                if not signer_dir.is_dir():
                    continue
                signer_id = signer_dir.name

                for img in signer_dir.glob('*.png'):
                    results.append({
                        'file_path': str(img),
                        'label': subdir == 'forged',
                        'script': script,
                        'signer_id': signer_id,
                        'file_hash': self.hash_file(img),
                    })

        return results

    def load_to_db(self, records: List[dict]) -> int:
        """Load records into PostgreSQL."""
        with get_session() as session:
            for rec in records:
                session.execute(
                    text('''
                        INSERT INTO documents
                        (file_path, label, script, signer_id)
                        VALUES (:file_path, :label, :script, :signer_id)
                    '''),
                    rec,
                )
        return len(records)

    def load_all(self) -> dict:
        """Load all genuine + forged data."""
        genuine = self.scan_directory('genuine')
        forged = self.scan_directory('forged')

        print(f'Found: {len(genuine)} genuine, {len(forged)} forged')

        total = self.load_to_db(genuine + forged)
        return {
            'genuine': len(genuine),
            'forged': len(forged),
            'total': total,
        }


if __name__ == '__main__':
    loader = SignatureDataLoader()
    result = loader.load_all()
    print(f'Loaded: {result}')