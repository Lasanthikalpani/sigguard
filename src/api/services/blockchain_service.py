"""
RQ3: Simple Blockchain Ledger Service

Implements a document-wise blockchain ledger for RQ3.

Purpose (Supervisor's comment):
- Store document records in an immutable ledger
- Support certified copies (timestamp changes, content stays same)
- Scale to millions of documents (e.g., 1980 birth certificates)

Design:
- Each document is a "block"
- Blocks are chained via prev_hash
- Ledger is append-only (immutable)
- Storage: JSON file (for prototype; production would use PostgreSQL)
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class BlockchainLedger:
    """
    Simple blockchain ledger for document authentication.
    """

    def __init__(self, ledger_path: str = "data/blockchain/ledger.json"):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self):
        if self.ledger_path.exists():
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                self.chain: List[Dict[str, Any]] = json.load(f)
        else:
            self.chain = [self._create_genesis_block()]
            self._save()

    def _save(self):
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            json.dump(self.chain, f, indent=2)

    def _create_genesis_block(self) -> Dict[str, Any]:
        return {
            "index": 0,
            "doc_id": "GENESIS",
            "content_hash": "0" * 64,
            "sig_hash": "0" * 64,
            "issuer": "SigGuard-LK",
            "issued_at": "2026-01-01T00:00:00Z",
            "prev_hash": "0" * 64,
            "block_hash": hashlib.sha256(b"genesis").hexdigest(),
        }

    def _compute_block_hash(self, block: Dict[str, Any]) -> str:
        block_copy = {k: v for k, v in block.items() if k != "block_hash"}
        canonical = json.dumps(block_copy, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()

    # ============================================================
    # ADD BLOCK
    # ============================================================

    def add_document(
        self,
        doc_id: str,
        content_hash: str,
        sig_hash: str,
        issuer: str = "GovLK",
        issued_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prev_block = self.chain[-1]
        new_block = {
            "index": len(self.chain),
            "doc_id": doc_id,
            "content_hash": content_hash,
            "sig_hash": sig_hash,
            "issuer": issuer,
            "issued_at": issued_at or datetime.utcnow().isoformat() + "Z",
            "prev_hash": prev_block["block_hash"],
            "metadata": metadata or {},
        }
        new_block["block_hash"] = self._compute_block_hash(new_block)
        self.chain.append(new_block)
        self._save()
        return new_block

    def add_certified_copy(
        self,
        original_doc_id: str,
        certifier: str = "GovLK",
    ) -> Dict[str, Any]:
        original = self.get_document(original_doc_id)
        if original is None:
            raise ValueError(f"Original document not found: {original_doc_id}")

        prev_block = self.chain[-1]
        new_block = {
            "index": len(self.chain),
            "doc_id": f"{original_doc_id}-COPY-{len(self.chain)}",
            "content_hash": original["content_hash"],           # SAME
            "sig_hash": original["sig_hash"],
            "issuer": certifier,
            "issued_at": datetime.utcnow().isoformat() + "Z",   # NEW
            "prev_hash": prev_block["block_hash"],
            "metadata": {
                "is_certified_copy": True,
                "original_doc_id": original_doc_id,
            },
        }
        new_block["block_hash"] = self._compute_block_hash(new_block)
        self.chain.append(new_block)
        self._save()
        return new_block

    # ============================================================
    # QUERY
    # ============================================================

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for block in self.chain:
            if block["doc_id"] == doc_id:
                return block
        return None

    def find_by_content_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        return [b for b in self.chain if b["content_hash"] == content_hash]

    def verify_chain(self) -> Dict[str, Any]:
        errors = []
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            if curr["prev_hash"] != prev["block_hash"]:
                errors.append(f"Block {i}: prev_hash mismatch")
            expected = self._compute_block_hash(curr)
            if curr["block_hash"] != expected:
                errors.append(f"Block {i}: block_hash mismatch")
        return {
            "valid": len(errors) == 0,
            "length": len(self.chain),
            "errors": errors,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_blocks": len(self.chain),
            "genesis_hash": self.chain[0]["block_hash"][:16] + "...",
            "latest_hash": self.chain[-1]["block_hash"][:16] + "...",
            "latest_index": self.chain[-1]["index"],
        }


# Singleton
_ledger = None


def get_ledger() -> BlockchainLedger:
    global _ledger
    if _ledger is None:
        _ledger = BlockchainLedger()
    return _ledger