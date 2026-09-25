## 8. Overfitting Analysis

### 8.1 Learning Curves

| Epoch | Train Loss | Val Loss |
|-------|------------|----------|
| 1 | 4.3174 | 0.2786 |
| 2 | 1.9520 | **0.1473** (best) |
| ... | ... | ... |
| 30 | 0.1551 | 0.2021 |

**Best epoch:** 2 (val loss: 0.1473)
**Final train loss:** 0.1551
**Final val loss:** 0.2021
**Train-val gap:** +0.0470

**Overfitting analysis:** Slight overfitting detected after epoch 2.

### 8.2 Feature Importance

Per-signer accuracy:

| Signer | Accuracy |
|--------|----------|
| signer_11 | 100% |
| signer_21 | 100% |
| signer_45 | 72.73% |
| signer_49 | 54.55% |
| signer_15 | 45.45% |

**Hard signers:** signer_15, signer_49, signer_45
**Recommendation:** More training data for hard signers.