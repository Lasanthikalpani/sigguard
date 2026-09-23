"""Import English signature dataset into SigGuard structure.

File formats:
    Genuine: original_<signer>_<sig>.png
    Forged:  forgeries_<signer>_<sig>.png
"""
import shutil
import re
import sys
from pathlib import Path


IMAGE_EXTENSIONS = ['*.png', '*.PNG', '*.jpg', '*.JPG',
                    '*.jpeg', '*.JPEG', '*.tif', '*.TIF',
                    '*.tiff', '*.TIFF']


def find_dir(source: Path, name: str):
    """Find a directory by name recursively."""
    for d in source.rglob(name):
        if d.is_dir():
            return d
    return None


def find_images(directory: Path):
    """Find all images in a directory (any format)."""
    images = []
    for ext in IMAGE_EXTENSIONS:
        images.extend(directory.glob(ext))
    return images


def parse_filename(stem: str):
    """Parse filename to extract signer ID and signature number.

    Supports:
        original_10_1     -> signer=10, sig=1
        forgeries_10_1    -> signer=10, sig=1
        forgery_10_1      -> signer=10, sig=1
        001_01            -> signer=001, sig=01
    """
    patterns = [
        r'original_(\d+)_(\d+)',
        r'forgeries_(\d+)_(\d+)',
        r'forgery_(\d+)_(\d+)',
        r'forg_(\d+)_(\d+)',
        r'(\d+)_(\d+)',
    ]

    for pattern in patterns:
        match = re.match(pattern, stem)
        if match:
            return match.group(1), match.group(2)

    return None, None


def import_english_dataset(source_dir: str, target_dir: str = 'data'):
    """Import English signatures into SigGuard."""
    source = Path(source_dir)
    target = Path(target_dir)

    if not source.exists():
        print(f'[ERROR] Source not found: {source}')
        return

    genuine_dir = find_dir(source, 'full_org')
    forged_dir = find_dir(source, 'full_forg')

    if not genuine_dir:
        print('[ERROR] full_org directory not found')
        return

    print(f'Genuine: {genuine_dir}')
    print(f'Forged:  {forged_dir}')

    genuine_images = find_images(genuine_dir)
    forged_images = find_images(forged_dir) if forged_dir else []

    print(f'Found images: {len(genuine_images)} genuine, {len(forged_images)} forged')

    # Group by signer ID
    signers = {}

    for img in genuine_images:
        signer_id, sig_id = parse_filename(img.stem)
        if signer_id:
            signers.setdefault(signer_id, {'genuine': [], 'forged': []})
            signers[signer_id]['genuine'].append(img)

    for img in forged_images:
        signer_id, sig_id = parse_filename(img.stem)
        if signer_id:
            signers.setdefault(signer_id, {'genuine': [], 'forged': []})
            signers[signer_id]['forged'].append(img)

    print(f'Found {len(signers)} signers')

    # Count matched
    total_genuine_files = sum(len(f['genuine']) for f in signers.values())
    total_forged_files = sum(len(f['forged']) for f in signers.values())
    print(f'Matched: {total_genuine_files} genuine, {total_forged_files} forged')

    # Copy to target
    total_genuine = 0
    total_forged = 0

    for signer_id, files in signers.items():
        # Genuine
        signer_target = target / 'genuine' / 'english' / f'signer_{signer_id}'
        signer_target.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(files['genuine'][:5], start=1):
            dest = signer_target / f'sig_{i:03d}.png'
            shutil.copy(img, dest)
            total_genuine += 1

        # Forged
        signer_target = target / 'forged' / 'english' / f'signer_{signer_id}'
        signer_target.mkdir(parents=True, exist_ok=True)

        for i, img in enumerate(files['forged'][:5], start=1):
            dest = signer_target / f'forged_{i:03d}.png'
            shutil.copy(img, dest)
            total_forged += 1

    print(f'[OK] Imported: {total_genuine} genuine, {total_forged} forged')
    print(f'     Signers: {len(signers)}')
    print(f'     Target: {target}')


if __name__ == '__main__':
    if len(sys.argv) > 1:
        source = sys.argv[1]
    else:
        source = input('Dataset directory: ').strip().strip('"').strip("'")

    import_english_dataset(source)