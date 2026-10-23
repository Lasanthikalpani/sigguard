"""
RQ3: Simple Blockchain Ledger Service

Implements a document-wise blockchain ledger for RQ3.

Purpose (Supervisor's comment):
- Store document records in an immutable ledger
- Support certified copies (timestamp changes, content stays same)
- Support amendments (Layer 5: content changes, lineage preserved)
- Scale to millions of documents (e.g., 1980 birth certificates)

Design:
- Each document is a "block"
- Blocks are chained via prev_hash
- Ledger is append-only (immutable)
- Storage: JSON file (for prototype; production would use PostgreSQL)
"""
import hashlib
import json
# src/api/services/blockchain_service.py — imports වලට පසුව

NODE_MAP = {
    "BIRTH_CERTIFICATE": "ledger_birth_certs.json",
    "LAND_DEED":         "ledger_land_deeds.json",
    "NATIONAL_ID":       "ledger_national_ids.json",
    "EDUCATION_CERT":    "ledger_education_certs.json",
    "VEHICLE_REG":       "ledger_vehicle_reg.json",
}

LEDGER_DIR = "data/rq3_dataset/blockchain"
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional


class BlockchainLedger:
    """
    Simple blockchain ledger for document authentication.
    """

    def __init__(self, ledger_path: str = None, document_type: str = None):
        if ledger_path:
            self.ledger_path = Path(ledger_path)
        elif document_type:
            # 🆕 Global NODE_MAP භාවිත කරන්න
            node_file = NODE_MAP.get(document_type, "ledger_unknown.json")
            self.ledger_path = Path(f"{LEDGER_DIR}/{node_file}")
        else:
            self.ledger_path = Path("data/blockchain/ledger.json")
        
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain = []           # ← NEW: Initialize chain
        self._load()

    def _load(self):
        if self.ledger_path.exists():
            with open(self.ledger_path, 'r') as f:
                data = json.load(f)
            
            # 🆕 ගොනුවේ ව්‍යුහය හඳුනාගන්න
            if isinstance(data, dict) and "blocks" in data:
                self.chain = data["blocks"]
            elif isinstance(data, list):
                self.chain = data
            else:
                self.chain = [self._create_genesis_block()]
                self._save()
            
            # 🆕 chain හිස් නම්, GENESIS එකතු කරන්න
            if not self.chain:
                self.chain = [self._create_genesis_block()]
                self._save()
        else:
            self.chain = [self._create_genesis_block()]
            self._save()

    def _save(self):
        with open(self.ledger_path, "w", encoding="utf-8") as f:
            # 🆕 ගොනුවේ ව්‍යුහයට ගැළපෙන ලෙස සුරකින්න
            json.dump({
                "blocks": self.chain,
                "genesis_hash": self.chain[0]["block_hash"] if self.chain else "0"*64
            }, f, indent=2)

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
        # 🆕 GENESIS block එක නොමැති නම්, එය සාදන්න
        if not self.chain:
            self.chain.append(self._create_genesis_block())
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

    # src/api/services/blockchain_service.py හි
    def add_certified_copy(self, original_doc_id, certifier):
        original = self.get_document(original_doc_id)
        if not original:
            raise ValueError("Original document not found")
#   🆕 doc_id හෝ document_id යන දෙකෙන් එකක් ලබා ගන්න
        doc_id = original.get("doc_id") or original.get("document_id")
        if not doc_id:
            raise ValueError("Original document has no doc_id or document_id")
        new_block = {
        "index": len(self.chain),
        "doc_id": original_doc_id,
        "content_hash": original["content_hash"],  # SAME
        "sig_hash": original["sig_hash"],          # SAME
        "issuer": certifier,
        "issued_at": datetime.utcnow().isoformat() + "Z",  # NEW timestamp
        "prev_hash": self.chain[-1]["block_hash"],
        "metadata": {
            "document_type": original["metadata"]["document_type"],
            "document_status": "CERTIFIED_COPY",   # ← NEW status
            "metadata_hash": original["metadata"]["metadata_hash"],  # SAME
            "phash": original["metadata"]["phash"],  # SAME
            "copy_of": original_doc_id  # ← Reference to original
        }
    }
        new_block["block_hash"] = self._compute_block_hash(new_block)
        self.chain.append(new_block)
        self._save()
        return new_block


    # ============================================================
    # LAYER 5: DOCUMENT AMENDMENT
    # ============================================================

    def add_amendment(self, original_doc_id, new_content_hash, new_sig_hash,
                      issuer, new_doc_id, amendment_reason, issued_at=None):
        """
        Add an AMENDED document to the blockchain.
        Also updates the original block's document_type to 'AMENDED'
        and sets 'superseded_by'.
        """
        # 1. Original block එක සොයන්න
        original = self.get_document(original_doc_id)
        if not original:
            raise ValueError(f"Original document not found: {original_doc_id}")

        # 2. Original block එක update කරන්න (superseded_by)
        original["metadata"]["document_status"] = "AMENDED"
        original["metadata"]["superseded_by"] = new_doc_id

        # 3. අලුත් AMENDED block එක සාදන්න
        new_block = {
            "index": len(self.chain),
            "doc_id": new_doc_id,
            "content_hash": new_content_hash,
            "sig_hash": new_sig_hash,
            "issuer": issuer,
            "issued_at": issued_at or datetime.utcnow().isoformat() + "Z",
            "prev_hash": self.chain[-1]["block_hash"],
            "metadata": {
                "document_type": original["metadata"].get("document_type", "BIRTH_CERTIFICATE"),
                "document_status": "AMENDED",
                "metadata_hash": new_content_hash,  # New metadata hash
                "phash": "",  # Amended documents may not have pHash
                "amends": original_doc_id,
                "copy_of": None,
                "amendment_reason": amendment_reason,
            }
        }
        new_block["block_hash"] = self._compute_block_hash(new_block)
        self.chain.append(new_block)
        self._save()
        return new_block
    

    def get_amendments(self, original_doc_id: str) -> List[Dict[str, Any]]:
        """Return all amendment blocks for a given original document."""
        return [
            b for b in self.chain
            if b.get("metadata", {}).get("original_doc_id") == original_doc_id
            and b.get("metadata", {}).get("is_amendment", False)
        ]

    def get_amendment_chain(self, doc_id: str) -> List[Dict[str, Any]]:
        """Return the full lineage of a document."""
        block = self.get_document(doc_id)
        if block is None:
            return []

        current = block
        while current.get("metadata", {}).get("is_amendment", False):
            original_id = current["metadata"].get("original_doc_id")
            parent = self.get_document(original_id)
            if parent is None:
                break
            current = parent

        original = current
        chain = [original]
        chain.extend(self.get_amendments(original["doc_id"]))
        return chain

    # ============================================================
    # QUERY
    # ============================================================

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for block in self.chain:
            # 🆕 doc_id හෝ document_id යන දෙකෙන් එකක් පරීක්ෂා කරන්න
            if block.get("doc_id") == doc_id or block.get("document_id") == doc_id:
                return block
        return None
    def find_by_content_hash(self, content_hash: str) -> List[Dict[str, Any]]:
        # 🆕 content_hash යන key එක නොමැති බ්ලොක් නොසලකා හරින්න
        return [b for b in self.chain if b.get("content_hash") == content_hash]

    def verify_chain(self) -> Dict[str, Any]:
        errors = []
        for i in range(1, len(self.chain)):
            prev = self.chain[i - 1]
            curr = self.chain[i]
            # 🆕 .get() භාවිත කරන්න
            if curr.get("prev_hash") != prev.get("block_hash"):
                errors.append(f"Block {i}: prev_hash mismatch")
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

_ledgers = {}

def get_ledger(document_type: str = None) -> BlockchainLedger:
    """Get the correct ledger node for a document type."""
    global _ledgers
    key = document_type or "default"
    if key not in _ledgers:
        if document_type:
            _ledgers[key] = BlockchainLedger(document_type=document_type)
        else:
            _ledgers[key] = BlockchainLedger()
    return _ledgers[key]
# src/api/services/blockchain_service.py අවසානයට

import time

# ============================================================
# BENCHMARK: Single Chain (O(N)) vs Group-wise Nodes (O(N/k))
# ============================================================
# ============================================================
# BENCHMARK: Single Chain (O(N)) vs Group-wise Nodes (O(N/k))
# ============================================================
def benchmark_single_chain_vs_group_wise(doc_id: str, document_type: str):
    """
    Compare Single Chain (O(N)) vs Group-wise Nodes (O(N/k)).
    Returns the time taken for each.
    """
    import os
    import json
    import time

    # 🆕 NODE_MAP සහ LEDGER_DIR ශ්‍රිතය තුළම නිර්වචනය කරන්න
    NODE_MAP = {
        "BIRTH_CERTIFICATE": "ledger_birth_certs.json",
        "LAND_DEED":         "ledger_land_deeds.json",
        "NATIONAL_ID":       "ledger_national_ids.json",
        "EDUCATION_CERT":    "ledger_education_certs.json",
        "VEHICLE_REG":       "ledger_vehicle_reg.json",
    }
    LEDGER_DIR = "data/rq3_dataset/blockchain"

    # 1. Single Chain (සියලුම nodes එකට)
    all_nodes = list(NODE_MAP.values())
    
    # 2. Group-wise Node (එක් node එකක් පමණි)
    target_node = NODE_MAP.get(document_type, "ledger_unknown.json")
    
    # ============================================================
    # --- Single Chain Simulation (O(N)) ---
    # ============================================================
    start_time = time.perf_counter()
    total_blocks_scanned = 0
    found_in = None
    
    for node_file in all_nodes:
        node_path = os.path.join(LEDGER_DIR, node_file)
        if not os.path.exists(node_path):
            continue
        
        with open(node_path, 'r') as f:
            data = json.load(f)
        
        # ගොනුවේ ව්‍යුහය dict එකක්ද ({"blocks": []}) නැත්නම් list එකක්ද යන්න පරීක්ෂා කරන්න
        blocks = data.get("blocks", []) if isinstance(data, dict) else data
        total_blocks_scanned += len(blocks)
        
        for block in blocks:
            if block.get("doc_id") == doc_id or block.get("document_id") == doc_id:
                found_in = node_file
                # 🆕 මෙහි 'break' එකක් නොමැත. එබැවින් සියලුම ගොනු කියවයි.
    
    single_chain_time = time.perf_counter() - start_time
    
    # ============================================================
    # --- Group-wise Node Simulation (O(N/k)) ---
    # ============================================================
    start_time = time.perf_counter()
    target_blocks_scanned = 0
    target_path = os.path.join(LEDGER_DIR, target_node)
    
    if os.path.exists(target_path):
        with open(target_path, 'r') as f:
            data = json.load(f)
        blocks = data.get("blocks", []) if isinstance(data, dict) else data
        target_blocks_scanned = len(blocks)
        
        for block in blocks:
            if block.get("doc_id") == doc_id or block.get("document_id") == doc_id:
                found_in = target_node
                break   # ✅ මෙය රඳවා ගන්න (එක් node එකක් පමණි)
    
    group_wise_time = time.perf_counter() - start_time
    
    # ============================================================
    # --- Speedup Calculation ---
    # ============================================================
    speedup = single_chain_time / group_wise_time if group_wise_time > 0 else 0
    
    return {
        "doc_id": doc_id,
        "document_type": document_type,
        "single_chain": {
            "time_ms": round(single_chain_time * 1000, 2),
            "blocks_scanned": total_blocks_scanned,
            "complexity": "O(N)"
        },
        "group_wise": {
            "time_ms": round(group_wise_time * 1000, 2),
            "blocks_scanned": target_blocks_scanned,
            "complexity": "O(N/k)"
        },
        "speedup": round(speedup, 2),
        "found_in": found_in
    }