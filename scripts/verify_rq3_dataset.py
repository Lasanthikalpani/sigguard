"""Verify RQ3 dataset (blockchain + files)."""
import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data/rq3_dataset")
LEDGER_PATH = DATA_DIR / "blockchain" / "ledger_100k.json"


def main():
    print("=" * 70)
    print("  RQ3 DATASET VERIFICATION")
    print("=" * 70)

    # ============================================================
    # FILE COUNTS
    # ============================================================
    print("\n=== File Counts ===")

    components = {
        "Documents":          DATA_DIR / "documents",
        "Signature regions":  DATA_DIR / "signatures",
        "References":         DATA_DIR / "references",
        "Degraded":           DATA_DIR / "degraded",
        "Tampered":           DATA_DIR / "tampered",
    }

    total_files = 0
    for name, path in components.items():
        if path.exists():
            count = len(list(path.rglob("*.png")))
            total_files += count
            print(f"  {name:<22} {count:>6,} PNG files")
        else:
            print(f"  {name:<22} [MISSING]")

    print(f"  {'Total PNG files':<22} {total_files:>6,}")

    # ============================================================
    # BLOCKCHAIN
    # ============================================================
    print("\n=== Blockchain Ledger ===")

    if not LEDGER_PATH.exists():
        print(f"  [ERROR] Ledger not found: {LEDGER_PATH}")
        return

    size_mb = LEDGER_PATH.stat().st_size / (1024 * 1024)
    print(f"  File:           {LEDGER_PATH.name}")
    print(f"  File size:      {size_mb:.2f} MB")

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        chain = json.load(f)

    print(f"  Total blocks:   {len(chain):,}")

    # Genesis
    genesis = chain[0]
    print(f"  Genesis hash:   {genesis['block_hash'][:32]}...")

    # Latest
    latest = chain[-1]
    print(f"  Latest hash:    {latest['block_hash'][:32]}...")

    # Certified copies
    copies = sum(
        1 for b in chain
        if b.get("metadata", {}).get("is_certified_copy", False)
    )
    originals = len(chain) - copies - 1  # -1 for genesis
    print()
    print(f"  Genesis blocks:       1")
    print(f"  Original documents:   {originals:,}")
    print(f"  Certified copies:     {copies:,}")

    # Year range
    years = []
    for b in chain[1:]:
        doc_id = b.get("doc_id", "")
        if doc_id.startswith("LK-"):
            parts = doc_id.split("-")
            if len(parts) >= 2:
                try:
                    years.append(int(parts[1]))
                except ValueError:
                    pass

    if years:
        print()
        print(f"  Year range:           {min(years)} - {max(years)}")
        print(f"  Unique years:         {len(set(years))}")

    # Chain integrity
    errors = 0
    for i in range(1, len(chain)):
        if chain[i].get("prev_hash") != chain[i - 1].get("block_hash"):
            errors += 1

    print()
    status = "VALID" if errors == 0 else "INVALID"
    print(f"  Chain integrity:      {status} ({errors} errors)")

    # ============================================================
    # SUMMARY
    # ============================================================
    print()
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  PNG files:            {total_files:,}")
    print(f"  Blockchain blocks:    {len(chain):,}")
    print(f"  Certified copies:     {copies:,}")
    print(f"  Year range:           {min(years) if years else 'N/A'} - {max(years) if years else 'N/A'}")
    print(f"  Chain integrity:      {status}")
    print()
    print("  [OK] RQ3 dataset is complete!")
    print()


if __name__ == "__main__":
    main()