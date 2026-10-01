# RQ3 — Hybrid Integration: Tamper Detection Results

**Research Question:** How can QR-based cryptographic hashing be effectively integrated
with AI verification to create a robust hybrid authentication system with **≥95% tamper
detection reliability**?

---

## 1. Overall Metrics

| Metric | Value | Target | Status |
|---|---|---|---|
| Tamper Detection Rate (Recall) | **100.00%** | ≥ 95% | ✅ MET |
| False Positive Rate | 0.00% | ≤ 5% | ✅ |
| Precision | 100.00% | — | — |
| F1 Score | 100.00% | — | — |
| Accuracy | 100.00% | — | — |

### Confusion Matrix

|  | Declared Authentic | Declared Tampered |
|---|---|---|
| **Actually Authentic** | TN = 400 | FP = 0 |
| **Actually Tampered** | FN = 0 | TP = 300 |

**Total samples evaluated:** 700

---

## 2. Per-Category Breakdown

| Category | Ground Truth | Correct / Total | Accuracy |
|---|---|---|---|
| `clean` | Authentic | 100 / 100 | 100.0% |
| `degraded_aging` | Authentic | 100 / 100 | 100.0% |
| `degraded_blur` | Authentic | 100 / 100 | 100.0% |
| `degraded_lowdpi` | Authentic | 100 / 100 | 100.0% |
| `tampered_content` | Tampered | 100 / 100 | 100.0% |
| `tampered_qr` | Tampered | 100 / 100 | 100.0% |
| `tampered_qr_partial` | Tampered | 100 / 100 | 100.0% |

---

## 3. Layer 3 Verification Scenarios

The QR verification layer returns one of 5 statuses:

| Status | Meaning | Counted as |
|---|---|---|
| `FULLY_AUTHENTIC` | All 4 checks (content, metadata, signature, blockchain) passed | Authentic |
| `TAMPERED` | Content hash mismatch or signature invalid | Tampered |
| `METADATA_MODIFIED` | Metadata hash mismatch | Tampered |
| `QR_MISSING` | No QR code found in document | Tampered |
| `AUTHENTIC_NOT_IN_BLOCKCHAIN` | Content valid but not registered | Authentic |

---

## 4. Interpretation

- The hybrid system achieved a tamper detection rate of **100.00%** across 700 evaluated documents.
- False positive rate was **0.00%**, meaning 0 authentic documents were incorrectly flagged as tampered.
- The system correctly classified **700 / 700** documents overall (100.00% accuracy).

### Against the RQ3 Target

> **Target:** ≥ 95% tamper detection reliability  
> **Achieved:** 100.00%  
> **Status:** ✅ MET

---

## 5. Files Generated

- `docs/RQ3_results.md` — this report
- `docs/rq3_results.json` — raw metrics (machine-readable)
- `docs/rq3_confusion_matrix.png` — confusion matrix plot

## 6. Reproduce

```powershell
conda activate sigguard
python scripts/build_rq3_eval_dataset.py
python scripts/rq3_tamper_evaluation.py
```
