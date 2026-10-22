# scripts/synthetic/generate_all.py
"""
Master pipeline: generates ALL synthetic RQ3 data.
Run from project root:
    python scripts/synthetic/generate_all.py --full     # production (100k)
    python scripts/synthetic/generate_all.py --smoke    # quick test (500)
"""

import sys
import os

# =====================================================================
# Project Root එක sys.path වෙත එකතු කිරීම (ModuleNotFoundError වැළැක්වීමට)
# =====================================================================
# මෙම ගොනුව scripts/synthetic/ තුළ ඇති බැවින්, root එකට '..', '..' අවශ්‍ය වේ.
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import argparse
import time

def main(full: bool = True):
    t0 = time.time()
    n_per_cat = 20000 if full else 100
    
    # Signers configuration
    if full:
        n_signers_cfg = {"sinhala": 100, "tamil": 80, "english": 100}
    else:
        n_signers_cfg = {"sinhala": 5, "tamil": 5, "english": 5}

    # -----------------------------------------------------------------
    # 1. Generate Blockchain Ledgers
    # -----------------------------------------------------------------
    print(f"[1/5] Generating group-wise ledgers ({n_per_cat * 5:,} blocks)...")
    try:
        from scripts.synthetic.ledger_writer import generate_full_ledger
        generate_full_ledger(
            n_per_category=n_per_cat,
            output_dir="data/rq3_dataset/blockchain"
        )
    except Exception as e:
        print(f"Error in ledger generation: {e}")
        print("Please ensure 'scripts/synthetic/ledger_writer.py' exists and has 'generate_full_ledger' function.")

    # -----------------------------------------------------------------
    # 2. Generate Signatures
    # -----------------------------------------------------------------
    print("[2/5] Generating signatures...")
    try:
        from scripts.synthetic.signature_generator import generate_signature_set
        for script, n in n_signers_cfg.items():
            for signer in range(n):
                generate_signature_set(
                    script=script,
                    signer_id=signer,
                    output_dir="data/rq3_dataset/signatures"
                )
    except Exception as e:
        print(f"Error in signature generation: {e}")
        print("Please ensure 'scripts/synthetic/signature_generator.py' exists.")

    # -----------------------------------------------------------------
    # 3. Render Evaluation Set
    # -----------------------------------------------------------------
    print("[3/5] Rendering RQ3 evaluation set...")
    try:
        from scripts.synthetic.eval_generator import generate_eval_set
        generate_eval_set(
            output_dir="data/rq3_dataset",
            full=full
        )
    except Exception as e:
        print(f"Error in evaluation set generation: {e}")
        print("Please ensure 'scripts/synthetic/eval_generator.py' exists.")

    # -----------------------------------------------------------------
    # 4. Apply Tamper / Degradation / Amendment
    # -----------------------------------------------------------------
    print("[4/5] Applying tamper / degradation / amendment...")
    try:
        from scripts.synthetic.tamper_generator import generate_tampered
        from scripts.synthetic.degradation import generate_degraded
        from scripts.synthetic.amendment_generator import generate_amendments
        
        generate_tampered(output_dir="data/rq3_dataset", full=full)
        generate_degraded(output_dir="data/rq3_dataset", full=full)
        generate_amendments(output_dir="data/rq3_dataset", full=full)
    except Exception as e:
        print(f"Error in tamper/degradation/amendment generation: {e}")
        print("Please ensure all required generator scripts exist.")

    # -----------------------------------------------------------------
    # 5. Write Manifest
    # -----------------------------------------------------------------
    print("[5/5] Writing manifest...")
    try:
        from scripts.synthetic.manifest import write_manifest
        write_manifest(output_dir="data/rq3_dataset")
    except Exception as e:
        print(f"Error in manifest generation: {e}")
        # Manifest එකක් නොමැති වුවත්, දත්ත ජනනය සාර්ථක විය හැක.

    print(f"\nAll done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--full", action="store_true", default=True)
    g.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    
    # --smoke ලබා දී ඇත්නම් full=False ලෙස යවන්න
    main(full=not args.smoke)
    