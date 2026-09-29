"""
Fast blockchain generation for RQ3 dataset.

Builds 110,000 blocks WITHOUT saving to disk on every block.
Saves in batches of 5,000 for speed.
"""
import hashlib
import json
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

BLOCKCHAIN_PATH = Path("data/rq3_dataset/blockchain/ledger_100k.json")

NUM_DOCUMENTS = 100000
BATCH_SIZE = 5000


def compute_block_hash(block):
    """Compute SHA-256 hash of a block."""
    block_copy = {k: v for k, v in block.items() if k != "block_hash"}
    canonical = json.dumps(block_copy, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def main():
    print("=" * 70)
    print("  RQ3 Fast Blockchain Generation (110,000 blocks)")
    print("=" * 70)

    BLOCKCHAIN_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Genesis block
    genesis = {
        "index": 0,
        "doc_id": "GENESIS",
        "content_hash": "0" * 64,
        "sig_hash": "0" * 64,
        "issuer": "SigGuard-LK",
        "issued_at": "2026-01-01T00:00:00Z",
        "prev_hash": "0" * 64,
        "block_hash": hashlib.sha256(b"genesis").hexdigest(),
    }

    chain = [genesis]
    start_time = time.time()

    print(f"\n[INFO] Generating {NUM_DOCUMENTS:,} blocks...")
    print(f"[INFO] Batch size: {BATCH_SIZE:,}")

    for i in range(NUM_DOCUMENTS):
        year = 1980 + (i % 45)
        doc_id = f"LK-{year}-{i:08d}"
        content_hash = hashlib.sha256(f"content_{i}".encode()).hexdigest()
        sig_hash = hashlib.sha256(f"sig_{i}".encode()).hexdigest()

        prev_block = chain[-1]
        new_block = {
            "index": len(chain),
            "doc_id": doc_id,
            "content_hash": content_hash,
            "sig_hash": sig_hash,
            "issuer": "GovLK",
            "issued_at": f"{year}-01-01T00:00:00Z",
            "prev_hash": prev_block["block_hash"],
            "metadata": {},
        }
        new_block["block_hash"] = compute_block_hash(new_block)
        chain.append(new_block)

        # Add certified copy every 10th
        if i > 0 and i % 10 == 0:
            prev_block = chain[-1]
            copy_block = {
                "index": len(chain),
                "doc_id": f"{doc_id}-COPY-{len(chain)}",
                "content_hash": content_hash,       # SAME
                "sig_hash": sig_hash,
                "issuer": "GovLK",
                "issued_at": datetime.utcnow().isoformat() + "Z",  # NEW
                "prev_hash": prev_block["block_hash"],
                "metadata": {
                    "is_certified_copy": True,
                    "original_doc_id": doc_id,
                },
            }
            copy_block["block_hash"] = compute_block_hash(copy_block)
            chain.append(copy_block)

        # Progress + batch save
        if (i + 1) % BATCH_SIZE == 0:
            # Save to disk
            with open(BLOCKCHAIN_PATH, "w", encoding="utf-8") as f:
                json.dump(chain, f, indent=2)

            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (NUM_DOCUMENTS - i - 1) / rate
            size_mb = BLOCKCHAIN_PATH.stat().st_size / (1024 * 1024)

            print(f"   [{i+1:>7,}/{NUM_DOCUMENTS:,}] "
                  f"{len(chain):>7,} blocks | "
                  f"{size_mb:>6.2f} MB | "
                  f"{rate:>6.0f} blocks/s | "
                  f"ETA: {eta:>4.0f}s")

    # Final save
    with open(BLOCKCHAIN_PATH, "w", encoding="utf-8") as f:
        json.dump(chain, f, indent=2)

    total_time = time.time() - start_time
    size_mb = BLOCKCHAIN_PATH.stat().st_size / (1024 * 1024)

    print()
    print("=" * 70)
    print("  BLOCKCHAIN COMPLETE")
    print("=" * 70)
    print(f"\nTotal blocks:   {len(chain):,}")
    print(f"Total time:     {total_time:.0f}s ({total_time/60:.1f} min)")
    print(f"File size:      {size_mb:.2f} MB")
    print(f"Output:         {BLOCKCHAIN_PATH}")
    print()


if __name__ == "__main__":
    main()