"""Re-split signers based on common signers from data/splits/."""
import shutil
import random
from pathlib import Path
import json

SOURCE = Path('data/splits')
OUTPUT = Path('data/splits_v2')

# Find ALL common signers across all splits
all_common = set()

for split in ['train', 'val', 'test']:
    genuine_dir = SOURCE / split / 'genuine'
    forged_dir = SOURCE / split / 'forged'

    if not genuine_dir.exists() or not forged_dir.exists():
        continue

    genuine_signers = set(d.name for d in genuine_dir.iterdir() if d.is_dir())
    forged_signers = set(d.name for d in forged_dir.iterdir() if d.is_dir())
    common = genuine_signers & forged_signers

    all_common.update(common)

all_common = sorted(all_common)
print(f'Total common signers across all splits: {len(all_common)}')
print()

# Shuffle signers
random.seed(42)
random.shuffle(all_common)

# Re-split 70/15/15
n = len(all_common)
n_train = int(n * 0.70)
n_val = int(n * 0.15)

train_signers = sorted(all_common[:n_train])
val_signers = sorted(all_common[n_train:n_train + n_val])
test_signers = sorted(all_common[n_train + n_val:])

print(f'New split:')
print(f'  Train: {len(train_signers)} signers')
print(f'  Val:   {len(val_signers)} signers')
print(f'  Test:  {len(test_signers)} signers')
print()

# Clean output
if OUTPUT.exists():
    shutil.rmtree(OUTPUT)

for split in ['train', 'val', 'test']:
    for cls in ['genuine', 'forged']:
        (OUTPUT / split / cls).mkdir(parents=True, exist_ok=True)

# Find source for each signer
def find_signer_source(signer, cls):
    """Find the source directory for a signer in genuine/forged."""
    for split in ['train', 'val', 'test']:
        src = SOURCE / split / cls / signer
        if src.exists():
            return src
    return None

# Copy signers
def copy_signers(signer_list, split_name):
    count_g = 0
    count_f = 0

    for signer in signer_list:
        # Genuine
        src = find_signer_source(signer, 'genuine')
        if src:
            dst = OUTPUT / split_name / 'genuine' / signer
            shutil.copytree(src, dst, dirs_exist_ok=True)
            count_g += len(list(dst.glob('*.png')))

        # Forged
        src = find_signer_source(signer, 'forged')
        if src:
            dst = OUTPUT / split_name / 'forged' / signer
            shutil.copytree(src, dst, dirs_exist_ok=True)
            count_f += len(list(dst.glob('*.png')))

    return count_g, count_f

print('Copying train signers...')
train_g, train_f = copy_signers(train_signers, 'train')

print('Copying val signers...')
val_g, val_f = copy_signers(val_signers, 'val')

print('Copying test signers...')
test_g, test_f = copy_signers(test_signers, 'test')

# Verify
print()
print('=' * 60)
print('Verification')
print('=' * 60)

for split in ['train', 'val', 'test']:
    g_dir = OUTPUT / split / 'genuine'
    f_dir = OUTPUT / split / 'forged'

    g_signers = set(d.name for d in g_dir.iterdir() if d.is_dir())
    f_signers = set(d.name for d in f_dir.iterdir() if d.is_dir())
    common_split = g_signers & f_signers

    g_count = len(list(g_dir.rglob('*.png')))
    f_count = len(list(f_dir.rglob('*.png')))

    print(f'{split}:')
    print(f'  Genuine: {g_count} images, {len(g_signers)} signers')
    print(f'  Forged:  {f_count} images, {len(f_signers)} signers')
    print(f'  Common:  {len(common_split)} signers <- IMPORTANT')
    print()

with open('data/splits_v2_signers.json', 'w') as f:
    json.dump({
        'train': train_signers,
        'val': val_signers,
        'test': test_signers,
    }, f, indent=2)

print('OK Signer-based split created: data/splits_v2')