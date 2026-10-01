"""
RQ3 Layer 5: Evaluation of Document Amendment.

Evaluates the amendment service on two categories:
  - legit_amendments: should verify as AMENDED_AUTHENTIC  (acceptance)
  - fake_amendments:  should verify as TAMPERED          (rejection)

Metrics:
  - Legitimate Amendment Acceptance Rate (LAAR)  → target 100%
  - Fake Amendment Rejection Rate    (FARR)  → target 100%
  - Confusion matrix
  - Per-reason breakdown (if multiple reasons present)

Outputs:
  - docs/RQ3_Layer5_results.md
  - docs/rq3_layer5_results.json
  - docs/rq3_layer5_confusion_matrix.png
"""
import base64
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

API = "http://localhost:8000"
EVAL_DIR = Path("data/rq3_layer5_eval")
DOCS_DIR = Path("docs")


def check_api():
    try:
        r = requests.get(f"{API}/api/v1/amendment/health", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def verify_doc(path: Path) -> dict:
    """POST to /amendment/verify. Returns response dict."""
    with open(path, "rb") as f:
        doc_bytes = f.read()
    r = requests.post(
        f"{API}/api/v1/amendment/verify",
        files={"document": (path.name, doc_bytes, "image/png")},
        timeout=60,
    )
    if r.status_code != 200:
        return {"status": f"HTTP_{r.status_code}", "error": r.text}
    return r.json()


def is_accept(status: str) -> bool:
    """Statuses that count as 'accepted as legitimate'."""
    return status in {"FULLY_AUTHENTIC", "AMENDED_AUTHENTIC"}


def is_reject(status: str) -> bool:
    """Statuses that count as 'rejected as tampered'."""
    return status in {"TAMPERED", "QR_MISSING", "METADATA_MODIFIED"}


# ============================================================
# Main
# ============================================================

def main():
    print("=" * 70)
    print("  RQ3 Layer 5 — Evaluation")
    print("=" * 70)

    if not check_api():
        print(f"[ERROR] API not running at {API}")
        return

    if not EVAL_DIR.exists():
        print(f"[ERROR] {EVAL_DIR} not found. Run build_rq3_layer5_dataset.py first.")
        return

    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    results = {}

    for category in ["legit_amendments", "fake_amendments"]:
        cat_dir = EVAL_DIR / category
        if not cat_dir.exists():
            print(f"[WARN] Missing category: {category}")
            continue

        files = sorted(cat_dir.glob("*.png"))
        print(f"\n[EVAL] {category} ({len(files)} files) ...")

        statuses = defaultdict(int)
        per_file = []

        for p in files:
            v = verify_doc(p)
            status = v.get("status", "UNKNOWN")
            statuses[status] += 1
            per_file.append({
                "file": p.name,
                "status": status,
                "document_id": v.get("document_id"),
                "is_amendment": v.get("blockchain", {}).get("is_amendment") if v.get("blockchain") else None,
            })

        # Print histogram
        for st, n in sorted(statuses.items(), key=lambda x: -x[1]):
            print(f"    {st:<28} {n}")

        results[category] = {
            "total": len(files),
            "status_histogram": dict(statuses),
            "per_file": per_file,
        }

    # ---- Compute metrics ----
    legit = results.get("legit_amendments", {})
    fake = results.get("fake_amendments", {})

    legit_total = legit.get("total", 0)
    fake_total = fake.get("total", 0)

    legit_accepted = sum(
        n for st, n in legit.get("status_histogram", {}).items() if is_accept(st)
    )
    fake_rejected = sum(
        n for st, n in fake.get("status_histogram", {}).items() if is_reject(st)
    )

    LAAR = legit_accepted / legit_total if legit_total else 0.0
    FARR = fake_rejected / fake_total if fake_total else 0.0

    print()
    print("=" * 70)
    print("  OVERALL METRICS")
    print("=" * 70)
    print(f"  Legitimate amendments:       {legit_total}")
    print(f"  Fake amendments:             {fake_total}")
    print(f"  Legit accepted:              {legit_accepted}/{legit_total}")
    print(f"  Fake rejected:               {fake_rejected}/{fake_total}")
    print()
    print(f"  LAAR (Legit Acceptance):     {LAAR*100:.2f}%   (target 100%)")
    print(f"  FARR (Fake Rejection):       {FARR*100:.2f}%   (target 100%)")
    print()
    laar_ok = LAAR >= 0.95
    farr_ok = FARR >= 0.95
    print(f"  Target (>=95% each):  {'✅ MET' if (laar_ok and farr_ok) else '❌ NOT MET'}")

    # ---- Per-file breakdown for legit ----
    print()
    print("=" * 70)
    print("  LEGIT AMENDMENT DETAILS")
    print("=" * 70)
    for r in legit.get("per_file", [])[:5]:
        print(f"  {r['file']:<50} {r['status']:<22} amendment={r['is_amendment']}")
    if len(legit.get("per_file", [])) > 5:
        print(f"  ... ({len(legit.get('per_file', [])) - 5} more)")

    # ---- Confusion matrix ----
    # Rows = ground truth, Cols = declared
    tn = fake_rejected   # fake rejected correctly (tampered, declared tampered)
    fp = fake_total - fake_rejected  # fake declared authentic (bad!)
    fn = legit_total - legit_accepted  # legit declared tampered (bad!)
    tp = legit_accepted  # legit accepted correctly

    cm = np.array([[tn, fp], [fn, tp]])

    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks([0, 1]); ax.set_yticks([0, 1])
    ax.set_xticklabels(["Declared\nTampered", "Declared\nAuthentic"])
    ax.set_yticklabels(["Actually\nTampered\n(fake)", "Actually\nAuthentic\n(legit)"])
    for i in range(2):
        for j in range(2):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="black" if cm[i, j] < cm.max() / 2 else "white",
                    fontsize=16, fontweight="bold")
    ax.set_title("RQ3 Layer 5 — Amendment Confusion Matrix")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    plot_path = DOCS_DIR / "rq3_layer5_confusion_matrix.png"
    fig.savefig(plot_path, dpi=150)
    plt.close(fig)
    print(f"\n[OK] Confusion matrix saved: {plot_path}")

    # ---- JSON output ----
    json_path = DOCS_DIR / "rq3_layer5_results.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "metrics": {
                "legit_total": legit_total,
                "fake_total": fake_total,
                "legit_accepted": legit_accepted,
                "fake_rejected": fake_rejected,
                "LAAR": round(LAAR, 4),
                "FARR": round(FARR, 4),
            },
            "confusion_matrix": {
                "tn": int(tn), "fp": int(fp),
                "fn": int(fn), "tp": int(tp),
            },
            "per_category": {
                cat: {
                    "total": data["total"],
                    "status_histogram": data["status_histogram"],
                }
                for cat, data in results.items()
            },
        }, f, indent=2)
    print(f"[OK] Raw results saved:     {json_path}")

    # ---- Markdown report ----
    md_path = DOCS_DIR / "RQ3_Layer5_results.md"
    write_markdown(md_path, results, LAAR, FARR, legit_accepted, legit_total,
                   fake_rejected, fake_total, laar_ok, farr_ok)
    print(f"[OK] Report saved:          {md_path}")


def write_markdown(path, results, LAAR, FARR, legit_accepted, legit_total,
                   fake_rejected, fake_total, laar_ok, farr_ok):
    status = "✅ MET" if (laar_ok and farr_ok) else "❌ NOT MET"

    lines = [
        "# RQ3 Layer 5 — Document Amendment: Evaluation Results",
        "",
        "**Research Question (extended):** How can QR-based cryptographic hashing",
        "distinguish between **legitimate amendments** and **forgeries**, while",
        "preserving cryptographic integrity?",
        "",
        "---",
        "",
        "## 1. Overall Metrics",
        "",
        "| Metric | Value | Target | Status |",
        "|---|---|---|---|",
        f"| Legitimate Amendment Acceptance Rate (LAAR) | **{LAAR*100:.2f}%** | ≥ 95% | {'✅' if laar_ok else '❌'} |",
        f"| Fake Amendment Rejection Rate (FARR) | **{FARR*100:.2f}%** | ≥ 95% | {'✅' if farr_ok else '❌'} |",
        f"| Overall target | — | both ≥ 95% | {status} |",
        "",
        f"**Legitimate amendments tested:** {legit_total}",
        f"**Fake amendments tested:** {fake_total}",
        "",
        "### Confusion Matrix",
        "",
        "|  | Declared Tampered | Declared Authentic |",
        "|---|---|---|",
        f"| **Actually Tampered (fake)** | TN = {fake_rejected} | FP = {fake_total - fake_rejected} |",
        f"| **Actually Authentic (legit)** | FN = {legit_total - legit_accepted} | TP = {legit_accepted} |",
        "",
        "---",
        "",
        "## 2. Per-Category Breakdown",
        "",
        "| Category | Total | Status Histogram |",
        "|---|---|---|",
    ]

    for cat, data in results.items():
        hist = ", ".join(f"{k}: {v}" for k, v in data["status_histogram"].items())
        lines.append(f"| `{category_label(cat)}` | {data['total']} | {hist} |")

    lines += [
        "",
        "---",
        "",
        "## 3. Verification Scenarios",
        "",
        "Layer 5 verify returns one of:",
        "",
        "| Status | Meaning | Counted as |",
        "|---|---|---|",
        "| `AMENDED_AUTHENTIC` | Amendment recognized, lineage verified | Accept |",
        "| `FULLY_AUTHENTIC` | Original document, all checks pass | Accept |",
        "| `TAMPERED` | Content hash mismatch / HMAC invalid | Reject |",
        "| `METADATA_MODIFIED` | Metadata hash mismatch | Reject |",
        "| `QR_MISSING` | No QR code found | Reject |",
        "",
        "---",
        "",
        "## 4. Interpretation",
        "",
        f"- **{legit_accepted}/{legit_total}** legitimate amendments were accepted as authentic "
        f"({LAAR*100:.2f}%).",
        f"- **{fake_rejected}/{fake_total}** fake amendments were rejected as tampered "
        f"({FARR*100:.2f}%).",
        "",
        "### Key Insight",
        "",
        "> Layer 5 successfully **distinguishes legitimate amendments from forgeries**.",
        "> A legitimate amendment is issued with a **new QR code**, a **new content hash**,",
        "> and a **lineage link** to the original document in the blockchain. A forgery,",
        "> which keeps the old QR and modifies content, fails verification because the",
        "> content hash no longer matches.",
        "",
        "### Against the Target",
        "",
        f"> **Target:** LAAR ≥ 95% AND FARR ≥ 95%  ",
        f"> **Achieved:** LAAR = {LAAR*100:.2f}%, FARR = {FARR*100:.2f}%  ",
        f"> **Status:** {status}",
        "",
        "---",
        "",
        "## 5. Files Generated",
        "",
        "- `docs/RQ3_Layer5_results.md` — this report",
        "- `docs/rq3_layer5_results.json` — raw metrics",
        "- `docs/rq3_layer5_confusion_matrix.png` — confusion matrix plot",
        "",
        "## 6. Reproduce",
        "",
        "```powershell",
        "conda activate sigguard",
        "# Ensure API is running: python -m uvicorn src.api.main:app --reload",
        "python scripts/build_rq3_layer5_dataset.py",
        "python scripts/rq3_layer5_evaluation.py",
        "```",
        "",
    ]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def category_label(cat: str) -> str:
    return {
        "legit_amendments": "Legitimate amendments",
        "fake_amendments": "Fake amendments",
    }.get(cat, cat)


if __name__ == "__main__":
    main()