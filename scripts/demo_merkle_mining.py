"""
Demo: Merkle Tree + Block Mining with 2000 documents.

Follows SigVerify research theory:
- 2000 birth certificates → 1 block
- 11-level Merkle Tree
- Proof-of-Work mining
- 99.95% storage reduction
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.merkle_service import MerkleTree
from src.api.services.mining_service import MiningService


def main():
    print("=" * 70)
    print("  SigVerify Block Mining Demo — 2000 Documents")
    print("=" * 70)

    # Create fresh chain
    path = Path("data/blockchain/demo_mining_chain.json")
    if path.exists():
        path.unlink()

    service = MiningService(
        batch_size=2000,
        difficulty=2,
        chain_path=str(path),
    )

    print(f"\n[1/4] Generating 2000 birth certificates...")

    start = time.time()
    for i in range(2000):
        doc = {
            "doc_id": f"BC-2026-{i:06d}",
            "content_hash": f"hash-{i}",
            "issuer": "Registrar General's Office",
            "issued_at": "2026-01-15T10:30:00",
        }
        result = service.add_document(doc)

        if (i + 1) % 500 == 0:
            print(f"   Generated {i + 1}/2000 documents")

    elapsed = time.time() - start

    # After loop, block should be mined
    print(f"\n[2/4] Mining block with 2000 transactions...")

    block = service.chain[-1]
    print(f"   Block {block.index} mined in {elapsed:.2f}s")
    print(f"   Merkle Root:  {block.merkle_root[:32]}...")
    print(f"   Block Hash:   {block.hash[:32]}...")
    print(f"   Nonce:        {block.nonce}")
    print(f"   Chain length: {len(service.chain)} block(s)")

    # Storage reduction
    print(f"\n[3/4] Storage Analysis:")
    stats = MerkleTree([f"doc-{i}" for i in range(2000)]).get_stats()
    print(f"   Traditional: {stats['traditional_size_bytes']:,} bytes (128 KB)")
    print(f"   Merkle Root: {stats['root_size_bytes']} bytes")
    print(f"   Reduction:   {stats['storage_reduction_pct']}%")

    # Verification speed
    print(f"\n[4/4] Verification Speed:")
    print(f"   Linear search:  2000 steps")
    print(f"   Merkle Tree:    {stats['verification_steps']} steps")
    print(f"   Speedup:        {2000 // stats['verification_steps']}x")

    # Merkle Proof validation
    print(f"\n[5/5] Merkle Proof Validation:")
    docs = [f"doc-{i}" for i in range(2000)]
    mt = MerkleTree(docs)
    proof = mt.get_proof(1500)
    leaf_hash = mt.hash_transaction(docs[1500])
    is_valid = MerkleTree.verify_proof(leaf_hash, proof, mt.get_root())
    print(f"   Proof for doc #1500: {'VALID' if is_valid else 'INVALID'}")
    print(f"   Proof length:        {len(proof)} hashes")

    # Tamper detection test
    print(f"\n[6/6] Tamper Detection:")
    tampered_docs = docs[:]
    tampered_docs[1500] = "TAMPERED"
    tampered_root = MerkleTree(tampered_docs).get_root()
    print(f"   Original root: {mt.get_root()[:32]}...")
    print(f"   Tampered root: {tampered_root[:32]}...")
    print(f"   Detected:      {'YES' if mt.get_root() != tampered_root else 'NO'}")

    print()
    print("=" * 70)
    print("  DEMO COMPLETE")
    print("=" * 70)
    print()


if __name__ == "__main__":
    main()