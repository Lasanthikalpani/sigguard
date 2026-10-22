# scripts/synthetic/ledger_writer.py
"""
Group-wise blockchain ledger writer for RQ3.
Creates 5 separate ledger files (one per document category).
"""

import json
import os
import hashlib
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Node mapping: document_type → ledger filename
# ─────────────────────────────────────────────────────────────
NODE_MAP = {
    "BIRTH_CERTIFICATE": "ledger_birth_certs.json",
    "LAND_DEED":         "ledger_land_deeds.json",
    "NATIONAL_ID":       "ledger_national_ids.json",
    "EDUCATION_CERT":    "ledger_education_certs.json",
    "VEHICLE_REG":       "ledger_vehicle_reg.json",
}

# Default output directory (matches your VS Code structure)
DEFAULT_NODE_DIR = "data/rq3_dataset/blockchain"


# ─────────────────────────────────────────────────────────────
# Section 6.1 — write_block()
# ─────────────────────────────────────────────────────────────
def write_block(record: dict, block_data: dict, node_dir: str = DEFAULT_NODE_DIR) -> dict:
    """
    Append a block to the correct group-wise node ledger.

    Args:
        record:     DocumentRecord as dict (document_id, document_type, issuer, ...)
        block_data: dict with content_hash, metadata_hash, phash, signature
        node_dir:   directory holding the 5 ledger_*.json files

    Returns:
        The written block (dict)
    """
    filename = NODE_MAP[record["document_type"]]
    path = os.path.join(node_dir, filename)

    # Load existing chain or create new
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            chain = json.load(f)
    else:
        chain = {"blocks": [], "genesis_hash": None}

    # Link to previous block
    prev_hash = chain["blocks"][-1]["block_hash"] if chain["blocks"] else "0" * 64

    # Build block
    block = {
        "index":           len(chain["blocks"]),
        "document_id":     record["document_id"],
        "content_hash":    block_data["content_hash"],
        "metadata_hash":   block_data["metadata_hash"],
        "phash":           block_data["phash"],
        "signature":       block_data["signature"],
        "issuer":          record["issuer"],
        "issued_at":       record["issued_at"],
        "document_type":   record["document_type"],
        "amends":          record.get("amends"),
        "copy_of":         record.get("copy_of"),
        "prev_hash":       prev_hash,
    }
    block["block_hash"] = hashlib.sha256(
        json.dumps(block, sort_keys=True).encode("utf-8")
    ).hexdigest()

    chain["blocks"].append(block)
    if chain["genesis_hash"] is None:
        chain["genesis_hash"] = block["block_hash"]

    # Atomic write
    os.makedirs(node_dir, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(chain, f, indent=2)
    os.replace(tmp, path)

    return block


# ─────────────────────────────────────────────────────────────
# Section 6.2 — generate_full_ledger()
# ─────────────────────────────────────────────────────────────
def generate_full_ledger(n_per_category: int = 20000,
                         output_dir: str = DEFAULT_NODE_DIR,
                         start_index: int = 0) -> dict:
    """
    Generate the full 100k ledger across 5 group-wise nodes.

    Args:
        n_per_category: documents per category (default 20,000 → 100,000 total)
        output_dir:     where to write ledger_*.json
        start_index:    starting index (for resumable generation)

    Returns:
        Summary dict with counts per node.
    """
    # Lazy import to avoid circular dependency
    from scripts.synthetic.template_generator import generate_document
    from scripts.synthetic.hash_generator import compute_hashes_and_sign

    os.makedirs(output_dir, exist_ok=True)

    # Reset ledger files (fresh generation)
    for fn in NODE_MAP.values():
        p = os.path.join(output_dir, fn)
        if os.path.exists(p):
            os.remove(p)

    summary = {cat: 0 for cat in NODE_MAP}

    for cat in NODE_MAP:
        for i in range(start_index, start_index + n_per_category):
            record = generate_document(cat, idx=i)
            block_data = compute_hashes_and_sign(record)
            write_block(record, block_data, node_dir=output_dir)
            summary[cat] += 1

    # Write summary manifest
    manifest_path = os.path.join(output_dir, "_ledger_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_blocks": sum(summary.values()),
            "per_category": summary,
            "nodes": list(NODE_MAP.values()),
        }, f, indent=2)

    print(f"[ledger] Generated {sum(summary.values())} blocks across {len(NODE_MAP)} nodes")
    return summary


# ─────────────────────────────────────────────────────────────
# Utility — quick test when run directly
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Smoke test with small counts
    print("Smoke test: generating 10 docs per category...")
    generate_full_ledger(n_per_category=10,
                         output_dir="data/rq3_dataset/blockchain_test")
    print("Done. Check data/rq3_dataset/blockchain_test/")