# SigGuard Research Log

## 2026-09-24: RQ1 Metrics Analysis

### Experiment Runs

| run_id | acc | f1 | auc | passed | Notes |
|--------|-----|-----|-----|--------|-------|
| 17 | 0.6229 | 0.5097 | 0.7838 | f | Best synthetic run |
| 18 | 0.5398 | 0.3229 | 0.7838 | f | Synthetic |

**Target metrics (RQ1):**
- Accuracy: >= 0.92
- Precision: >= 0.90
- Recall: >= 0.90
- F1: >= 0.90
- AUC-ROC: >= 0.95

**Current status:**
- Accuracy: 0.6229 (far from 0.92)
- F1: 0.5097 (far from 0.90)
- AUC-ROC: 0.7838 (far from 0.95)

### Kaggle Model

- **File:** best_model_v7.pth
- **Epoch:** 8
- **Val loss:** 0.2128
- **Params:** 129

### Decision Threshold

- **Threshold:** 0.01
- **Genuine:** distance < 0.01
- **Forged:** distance >= 0.01

### Gap Analysis

**Why are metrics low?**
1. Synthetic test data (random polylines)
2. Model trained on [unknown data]
3. Only 8 epochs

**Next steps:**
1. Add real signature data (CEDAR, BHSig260, or custom)
2. Retrain model with real data
3. Run evaluation harness
4. Target: >= 0.92 accuracy

### Database Status

- **Active runs:** 17, 18
- **Deleted runs:** 1, 2, 5, 9 (fake test), 3, 4, 6, 7, 8, 10-16 (synthetic)
- **Total runs:** 2
