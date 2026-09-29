"""
Demo: Merkle Tree Verification Speed (O(log n)).

Theory (SigVerify research):
- 2000 docs: 11 steps (Merkle) vs 2000 steps (linear) = 182x speedup
- 100,000 docs: 17 steps vs 100,000 steps = 5,882x speedup
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.merkle_service import MerkleTree


def main():
    print("=" * 70)
    print("  Merkle Tree Verification Speed (SigVerify Theory)")
    print("=" * 70)

    print(f"\n{'Documents':>12} {'Linear':>10} {'Merkle':>10} {'Speedup':>12} {'Build Time':>14}")
    print("-" * 70)

    for n in [100, 1000, 2000, 10000, 100000, 1000000]:
        docs = [f"doc-{i}" for i in range(n)]

        start = time.time()
        mt = MerkleTree(docs)
        build_time = time.time() - start

        stats = mt.get_stats()

        linear = n
        merkle = stats["verification_steps"]
        speedup = linear // max(merkle, 1)

        print(f"{n:>12,} {linear:>10,} {merkle:>10} {speedup:>11}x {build_time*1000:>11.1f} ms")

    print()
    print("=" * 70)
    print("  Key Insight:")
    print("  - When documents double, Merkle Tree steps increase by only 1")
    print("  - Storage stays at 64 bytes (1 root hash) regardless of N")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()