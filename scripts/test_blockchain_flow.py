"""
RQ3 Blockchain Full Flow Test (Python version).

Tests:
1. Issue document (adds to blockchain)
2. Ledger stats
3. Lookup by doc_id
4. Issue certified copy (same content hash!)
5. Find by content hash
6. Verify chain
"""
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"


def main():
    print("=" * 60)
    print("  RQ3 Blockchain Full Flow Test")
    print("=" * 60)

    # ============================================================
    # STEP 1: Issue Document
    # ============================================================
    print("\n=== STEP 1: Issue Document ===")
    doc_path = Path("test_data/documents/doc_01_land_deed.png")
    sig_path = Path("test_data/signatures/sig_01_sinhala.png")

    with open(doc_path, "rb") as f:
        doc_bytes = f.read()
    with open(sig_path, "rb") as f:
        sig_bytes = f.read()

    r = requests.post(
        f"{API}/api/v1/hybrid/issue-and-embed",
        files={
            "document": (doc_path.name, doc_bytes, "image/png"),
            "signature": (sig_path.name, sig_bytes, "image/png"),
        },
        data={"issuer": "Government of Sri Lanka", "ai_confidence": "0.95"},
        timeout=60,
    )

    if r.status_code != 200:
        print(f"[ERROR] Issue failed: {r.status_code} — {r.text}")
        return

    response = r.json()
    doc_id = response["document_id"]
    block_hash = response.get("blockchain", {}).get("block_hash")
    block_index = response.get("blockchain", {}).get("block_index")

    print(f"Document ID:  {doc_id}")
    print(f"Block hash:   {block_hash}")
    print(f"Block index:  {block_index}")

    # ============================================================
    # STEP 2: Ledger stats (should be 2 blocks now)
    # ============================================================
    print("\n=== STEP 2: Ledger stats ===")
    r = requests.get(f"{API}/api/v1/hybrid/ledger/stats")
    stats = r.json()
    print(f"Total blocks: {stats['stats']['total_blocks']}")
    print(f"Latest index: {stats['stats']['latest_index']}")

    # ============================================================
    # STEP 3: Lookup by doc_id
    # ============================================================
    print("\n=== STEP 3: Lookup document ===")
    r = requests.post(
        f"{API}/api/v1/hybrid/ledger/lookup",
        json={"doc_id": doc_id},
    )
    if r.status_code != 200:
        print(f"[ERROR] Lookup failed: {r.status_code} — {r.text}")
        return

    lookup = r.json()
    block = lookup["block"]
    content_hash = block["content_hash"]
    print(f"Found:        {block['doc_id']}")
    print(f"Content hash: {content_hash[:32]}...")

    # ============================================================
    # STEP 4: Issue Certified Copy (Supervisor's key insight!)
    # ============================================================
    print("\n=== STEP 4: Issue Certified Copy ===")
    r = requests.post(
        f"{API}/api/v1/hybrid/ledger/certified-copy",
        json={
            "original_doc_id": doc_id,
            "certifier": "Government of Sri Lanka",
        },
    )

    if r.status_code != 200:
        print(f"[ERROR] Certified copy failed: {r.status_code} — {r.text}")
        return

    copy_result = r.json()
    copy_block = copy_result["certified_copy"]
    print(f"Certified ID: {copy_block['doc_id']}")
    print(f"Same content: {copy_block['content_hash'] == content_hash}")
    print(f"New timestamp: {copy_block['issued_at']}")

    # ============================================================
    # STEP 5: Find by content hash (should return 2 matches)
    # ============================================================
    print("\n=== STEP 5: Find by content hash ===")
    r = requests.get(
        f"{API}/api/v1/hybrid/ledger/find-by-hash",
        params={"content_hash": content_hash},
    )
    find_result = r.json()
    print(f"Matches:      {find_result['matches']}")
    for blk in find_result["blocks"]:
        is_copy = blk.get("metadata", {}).get("is_certified_copy", False)
        label = " (COPY)" if is_copy else " (ORIGINAL)"
        print(f"  - {blk['doc_id']}{label}")

    # ============================================================
    # STEP 6: Final ledger stats
    # ============================================================
    print("\n=== STEP 6: Final ledger stats ===")
    r = requests.get(f"{API}/api/v1/hybrid/ledger/stats")
    final_stats = r.json()
    print(f"Total blocks: {final_stats['stats']['total_blocks']}")

    r = requests.get(f"{API}/api/v1/hybrid/ledger/verify-chain")
    verify = r.json()
    print(f"Chain valid:  {verify['valid']}")

    # ============================================================
    # SUMMARY
    # ============================================================
    print()
    print("=" * 60)
    print("  TEST COMPLETE")
    print("=" * 60)
    print()
    print(f"[OK] Issue document:       {doc_id}")
    print(f"[OK] Ledger:               {final_stats['stats']['total_blocks']} blocks")
    print(f"[OK] Certified copy:       {copy_block['doc_id']}")
    print(f"[OK] Same content hash:    {copy_block['content_hash'] == content_hash}")
    print(f"[OK] Matches found:        {find_result['matches']}")
    print(f"[OK] Chain valid:          {verify['valid']}")
    print()


if __name__ == "__main__":
    main()