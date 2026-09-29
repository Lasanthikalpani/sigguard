"""
Tests for Merkle Tree + Block Mining (RQ3 Theory).

Validates:
- Merkle Root computation (2000 docs → 1 hash)
- Storage reduction (128 KB → 64 bytes)
- Merkle Proof (O(log n) = 11 steps for 2000 docs)
- Tamper detection (100%)
- Proof-of-Work mining
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.services.merkle_service import MerkleTree
from src.api.services.mining_service import Block, MiningService


# ============================================================
# MERKLE TREE TESTS
# ============================================================

def test_merkle_tree_4_docs():
    """Build Merkle Tree with 4 documents (visual example)."""
    docs = ["Doc1", "Doc2", "Doc3", "Doc4"]
    mt = MerkleTree(docs)

    assert mt.get_root() is not None
    assert len(mt.get_root()) == 64
    assert len(mt.leaves) == 4
    assert len(mt.tree) == 3   # Level 0 + Level 1 + Level 2


def test_merkle_tree_root_changes_on_tamper():
    """Any change to a leaf changes the root (100% tamper detection)."""
    docs = ["Doc1", "Doc2", "Doc3", "Doc4"]
    root_original = MerkleTree(docs).get_root()

    # Tamper Doc3
    docs_tampered = ["Doc1", "Doc2", "TAMPERED", "Doc4"]
    root_tampered = MerkleTree(docs_tampered).get_root()

    assert root_original != root_tampered


def test_merkle_tree_2000_docs():
    """2000 documents → 11 levels (log₂ 2000 ≈ 11)."""
    docs = [f"BC-2026-{i:06d}" for i in range(2000)]
    mt = MerkleTree(docs)

    assert len(mt.leaves) == 2000
    assert len(mt.tree) == 12   # 11 levels + root (level 0 is leaves)
    # Levels: 2000 → 1000 → 500 → 250 → 125 → 63 → 32 → 16 → 8 → 4 → 2 → 1


def test_storage_reduction():
    """2000 docs → 1 root hash → 99.95% storage reduction."""
    docs = [f"doc-{i}" for i in range(2000)]
    mt = MerkleTree(docs)
    stats = mt.get_stats()

    assert stats["root_size_bytes"] == 64
    assert stats["traditional_size_bytes"] == 2000 * 64
    assert stats["storage_reduction_pct"] == 99.95
    assert stats["verification_steps"] == 11


def test_merkle_proof_valid():
    """Merkle Proof verification works."""
    docs = [f"doc-{i}" for i in range(16)]  # 16 → 4 levels
    mt = MerkleTree(docs)

    # Get proof for doc #5
    proof = mt.get_proof(5)

    # Verify
    leaf_hash = mt.hash_transaction(docs[5])
    is_valid = MerkleTree.verify_proof(leaf_hash, proof, mt.get_root())

    assert is_valid is True


def test_merkle_proof_rejects_tamper():
    """Merkle Proof fails when document is tampered."""
    docs = [f"doc-{i}" for i in range(16)]
    mt = MerkleTree(docs)

    proof = mt.get_proof(5)
    tampered_hash = mt.hash_transaction("TAMPERED")

    is_valid = MerkleTree.verify_proof(tampered_hash, proof, mt.get_root())
    assert is_valid is False


def test_merkle_tree_odd_number():
    """Odd number of leaves handled correctly."""
    docs = ["A", "B", "C"]  # 3 leaves (odd)
    mt = MerkleTree(docs)

    assert mt.get_root() is not None
    assert len(mt.leaves) == 3


# ============================================================
# BLOCK TESTS
# ============================================================

def test_block_hash_structure():
    """Block hash contains Merkle Root."""
    docs = [f"doc-{i}" for i in range(10)]
    blk = Block(index=1, transactions=docs, previous_hash="0" * 64)

    assert blk.merkle_root is not None
    assert blk.hash is not None
    assert len(blk.hash) == 64
    assert blk.index == 1


def test_block_pow_difficulty():
    """Block hash starts with '00' after mining."""
    docs = [f"doc-{i}" for i in range(5)]
    blk = Block(index=1, transactions=docs, previous_hash="0" * 64)

    # Manually mine
    prefix = "00"
    while not blk.hash.startswith(prefix):
        blk.nonce += 1
        blk.hash = blk.compute_hash()

    assert blk.hash.startswith("00")
    assert blk.nonce > 0


# ============================================================
# MINING SERVICE TESTS
# ============================================================

@pytest.fixture
def mining_service(tmp_path):
    """Create isolated mining service."""
    path = tmp_path / "test_chain.json"
    return MiningService(batch_size=10, difficulty=2, chain_path=str(path))


def test_mining_starts_at_batch_size(mining_service):
    """Mining triggers when batch_size is reached."""
    # Add 9 documents — should stay pending
    for i in range(9):
        result = mining_service.add_document(f"doc-{i}")

    assert result["status"] == "pending"
    assert result["pending_count"] == 9

    # Add 10th → mining triggers
    result = mining_service.add_document("doc-9")
    assert result["status"] == "mined"
    assert result["block"]["transaction_count"] == 10


def test_mining_clears_pending(mining_service):
    """After mining, pending_transactions is cleared."""
    for i in range(10):
        mining_service.add_document(f"doc-{i}")

    assert len(mining_service.pending_transactions) == 0
    assert len(mining_service.chain) == 2   # Genesis + Block 1


def test_mining_creates_valid_block(mining_service):
    """Mined block has valid structure."""
    for i in range(10):
        mining_service.add_document(f"doc-{i}")

    block = mining_service.chain[-1]

    assert block.index == 1
    assert block.previous_hash == mining_service.chain[0].hash
    assert block.hash.startswith("00")
    assert block.merkle_root is not None


def test_chain_stats(mining_service):
    """Chain stats are correct."""
    for i in range(10):
        mining_service.add_document(f"doc-{i}")

    stats = mining_service.get_chain_stats()

    assert stats["chain_length"] == 2
    assert stats["batch_size"] == 10
    assert stats["difficulty"] == 2
    assert stats["pending_transactions"] == 0


def test_2000_document_batch(tmp_path):
    """Test with 2000 documents (SigVerify production batch size)."""
    path = tmp_path / "big_chain.json"
    service = MiningService(batch_size=2000, difficulty=2, chain_path=str(path))

    for i in range(2000):
        result = service.add_document({"doc_id": f"BC-2026-{i:06d}"})

    assert result["status"] == "mined"
    assert len(service.chain) == 2
    block = service.chain[-1]
    assert block.index == 1
    assert block.hash.startswith("00")

    # Verify Merkle Root is present
    assert block.merkle_root is not None


def test_verification_steps_for_2000_docs():
    """Verification takes ~11 steps for 2000 docs (O(log n))."""
    stats = MerkleTree([f"d-{i}" for i in range(2000)]).get_stats()
    assert stats["verification_steps"] == 11


def test_linear_vs_merkle_speedup():
    """182x speedup for 2000 documents."""
    docs = 2000
    linear_steps = docs                # worst case: 2000
    merkle_steps = MerkleTree([f"d-{i}" for i in range(docs)]).get_stats()["verification_steps"]
    speedup = linear_steps / merkle_steps

    assert speedup > 180   # >180x speedup