"""
RQ3: Merkle Tree Service

Theory-based implementation following SigVerify research papers:
- Hash each document (leaf)
- Pair and hash recursively
- Get single Merkle Root
- Verify with Merkle Proof (O(log n) = 11 steps for 2000 docs)

References:
- SigVerify Block Mining (2000 docs per block)
- Merkle Tree Simple Implementation
- Correct Tamper Detection with Merkle Tree
- Merkle Tree Verification Speed
- Merkle Tree Storage Reduction

Only Python built-ins (hashlib, json) — no external libraries.
"""
import hashlib
import json
from typing import List, Dict, Any, Optional, Tuple


class MerkleTree:
    """
    Merkle Tree for SigVerify batch blockchain.

    Batching 2000 documents → 1 Merkle Root (64 bytes).
    Storage reduction: 128 KB → 64 bytes (99.95%).

    Verification: O(log n) = 11 steps for 2000 documents.
    Tamper detection: 100% (any change changes root).
    """

    def __init__(self, transactions: Optional[List[Any]] = None):
        """
        Initialize Merkle Tree.

        Args:
            transactions: List of document records (dicts or strings)
        """
        self.transactions = transactions or []
        self.leaves: List[str] = []
        self.tree: List[List[str]] = []
        self.root: Optional[str] = None

        if self.transactions:
            self.build()

    # ============================================================
    # HASHING
    # ============================================================

    @staticmethod
    def sha256(data: str) -> str:
        """Compute SHA-256 hash of a string."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_transaction(tx: Any) -> str:
        """
        Compute leaf hash of a transaction.

        Args:
            tx: Document record (dict) or string

        Returns:
            SHA-256 hex digest
        """
        if isinstance(tx, dict):
            canonical = json.dumps(tx, sort_keys=True, separators=(",", ":"))
        else:
            canonical = str(tx)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    # ============================================================
    # BUILD
    # ============================================================

    def build(self) -> str:
        """
        Build the Merkle Tree from transactions.

        Returns:
            Merkle Root hash (64-char hex string)

        Theory:
            1. Hash each transaction → leaves
            2. Pair adjacent leaves → hash each pair
            3. Repeat until one hash remains → root
        """
        # Step 1: Hash each transaction (Level 0 — leaves)
        self.leaves = [self.hash_transaction(tx) for tx in self.transactions]

        if not self.leaves:
            self.root = ""
            self.tree = [[]]
            return self.root

        # Step 2: Build tree level by level
        self.tree = [self.leaves[:]]
        current_level = self.leaves[:]

        while len(current_level) > 1:
            # If odd number, duplicate last
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])

            # Pair and hash
            next_level = []
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                next_level.append(self.sha256(combined))

            self.tree.append(next_level)
            current_level = next_level

        # Step 3: Root
        self.root = current_level[0]
        return self.root

    # ============================================================
    # GETTERS
    # ============================================================

    def get_root(self) -> Optional[str]:
        """Get the Merkle Root."""
        return self.root

    def get_proof(self, leaf_index: int) -> List[Dict[str, str]]:
        """
        Generate Merkle Proof for a leaf (document).

        Theory:
            Proof = sibling hashes along the path from leaf to root.
            For 2000 documents: log₂(2000) ≈ 11 siblings.

        Args:
            leaf_index: Index of the document (0-based)

        Returns:
            List of {'hash': sibling_hash, 'position': 'left'|'right'}
        """
        if not self.tree or leaf_index < 0 or leaf_index >= len(self.leaves):
            return []

        proof = []
        index = leaf_index

        for level in range(len(self.tree) - 1):
            current_level = self.tree[level]

            # Handle odd-level duplication
            if len(current_level) % 2 != 0:
                current_level = current_level + [current_level[-1]]

            # Sibling index
            if index % 2 == 0:
                sibling_index = index + 1
                position = "right"
            else:
                sibling_index = index - 1
                position = "left"

            if sibling_index < len(current_level):
                proof.append({
                    "hash": current_level[sibling_index],
                    "position": position,
                })

            # Move up
            index = index // 2

        return proof

    @staticmethod
    def verify_proof(
        leaf_hash: str,
        proof: List[Dict[str, str]],
        root: str,
    ) -> bool:
        """
        Verify a Merkle Proof.

        Theory:
            Recompute hashes along the path using sibling hashes.
            If final hash == root → valid.

        Args:
            leaf_hash: Hash of the leaf (document)
            proof: List of sibling hashes with positions
            root: Expected Merkle Root

        Returns:
            True if proof is valid
        """
        current = leaf_hash

        for step in proof:
            sibling = step["hash"]
            position = step["position"]

            if position == "left":
                combined = sibling + current
            else:
                combined = current + sibling

            current = hashlib.sha256(combined.encode("utf-8")).hexdigest()

        return current == root

    # ============================================================
    # STATS
    # ============================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get Merkle Tree statistics."""
        return {
            "transactions": len(self.transactions),
            "leaves": len(self.leaves),
            "levels": len(self.tree),
            "root": self.root,
            "root_size_bytes": 64,
            "traditional_size_bytes": len(self.leaves) * 64,
            "storage_reduction_pct": (
                round((1 - 64 / (len(self.leaves) * 64)) * 100, 2)
                if self.leaves else 0.0
            ),
            "verification_steps": (
                len(self.tree) - 1 if self.tree else 0
            ),
        }