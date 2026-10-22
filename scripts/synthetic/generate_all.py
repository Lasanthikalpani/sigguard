# scripts/synthetic/generate_all.py
"""
Master pipeline: generates ALL synthetic RQ3 data.
Run from project root:
    python -m scripts.synthetic.generate_all --full     # production (100k)
    python -m scripts.synthetic.generate_all --smoke    # quick test (500)
"""

import argparse
import time


def main(full: bool = True):
    t0 = time.time()
    n_per_cat = 20000 if full else 100
    n_signers_cfg = {"sinhala": 100, "tamil": 80, "english": 100} if full \
                    else {"sinhala": 5, "tamil": 5, "english": 5}

    print(f"[1/5] Generating group-wise ledgers "
          f"({n_per_cat * 5:,} blocks)...")
    from scripts.synthetic.ledger_writer import generate_full_ledger
    generate_full_ledger(n_per_category=n_per_cat,
                         output_dir="data/rq3_dataset/blockchain")

    print("[2/5] Generating signatures...")
    from scripts.synthetic.signature_generator import generate_signature_set
    for script, n in n_signers_cfg.items():
        for signer in range(n):
            generate_signature_set(
                script=script, signer_id=signer,
                output_dir="data/rq3_dataset/signatures")

    print("[3/5] Rendering RQ3 evaluation set...")
    from scripts.synthetic.eval_generator import generate_eval_set
    generate_eval_set(output_dir="data/rq3_dataset", full=full)

    print("[4/5] Applying tamper / degradation / amendment...")
    from scripts.synthetic.tamper_generator import generate_tampered
    from scripts.synthetic.degradation import generate_degraded
    from scripts.synthetic.amendment_generator import generate_amendments
    generate_tampered(output_dir="data/rq3_dataset", full=full)
    generate_degraded(output_dir="data/rq3_dataset", full=full)
    generate_amendments(output_dir="data/rq3_dataset", full=full)

    print("[5/5] Writing manifest...")
    from scripts.synthetic.manifest import write_manifest
    write_manifest(output_dir="data/rq3_dataset")

    print(f"\nAll done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--full",  action="store_true", default=True)
    g.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    main(full=not args.smoke)
    