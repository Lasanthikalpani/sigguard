# RQ3 Layer 5 — Document Amendment: Evaluation Results

**Research Question (extended):** How can QR-based cryptographic hashing
distinguish between **legitimate amendments** and **forgeries**, while
preserving cryptographic integrity?

---

## 1. Overall Metrics

| Metric | Value | Target | Status |
|---|---|---|---|
| Legitimate Amendment Acceptance Rate (LAAR) | **100.00%** | ≥ 95% | ✅ |
| Fake Amendment Rejection Rate (FARR) | **100.00%** | ≥ 95% | ✅ |
| Overall target | — | both ≥ 95% | ✅ MET |

**Legitimate amendments tested:** 50
**Fake amendments tested:** 50

### Confusion Matrix

|  | Declared Tampered | Declared Authentic |
|---|---|---|
| **Actually Tampered (fake)** | TN = 50 | FP = 0 |
| **Actually Authentic (legit)** | FN = 0 | TP = 50 |

---

## 2. Per-Category Breakdown

| Category | Total | Status Histogram |
|---|---|---|
| `Legitimate amendments` | 50 | AMENDED_AUTHENTIC: 50 |
| `Fake amendments` | 50 | TAMPERED: 50 |

---

## 3. Verification Scenarios

Layer 5 verify returns one of:

| Status | Meaning | Counted as |
|---|---|---|
| `AMENDED_AUTHENTIC` | Amendment recognized, lineage verified | Accept |
| `FULLY_AUTHENTIC` | Original document, all checks pass | Accept |
| `TAMPERED` | Content hash mismatch / HMAC invalid | Reject |
| `METADATA_MODIFIED` | Metadata hash mismatch | Reject |
| `QR_MISSING` | No QR code found | Reject |

---

## 4. Interpretation

- **50/50** legitimate amendments were accepted as authentic (100.00%).
- **50/50** fake amendments were rejected as tampered (100.00%).

### Key Insight

> Layer 5 successfully **distinguishes legitimate amendments from forgeries**.
> A legitimate amendment is issued with a **new QR code**, a **new content hash**,
> and a **lineage link** to the original document in the blockchain. A forgery,
> which keeps the old QR and modifies content, fails verification because the
> content hash no longer matches.

### Against the Target

> **Target:** LAAR ≥ 95% AND FARR ≥ 95%  
> **Achieved:** LAAR = 100.00%, FARR = 100.00%  
> **Status:** ✅ MET

---

## 5. Files Generated

- `docs/RQ3_Layer5_results.md` — this report
- `docs/rq3_layer5_results.json` — raw metrics
- `docs/rq3_layer5_confusion_matrix.png` — confusion matrix plot

## 6. Reproduce

```powershell
conda activate sigguard
# Ensure API is running: python -m uvicorn src.api.main:app --reload
python scripts/build_rq3_layer5_dataset.py
python scripts/rq3_layer5_evaluation.py
```
