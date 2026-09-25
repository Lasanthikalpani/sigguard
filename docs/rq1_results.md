\# RQ1: Core AI Performance — Final Results



\## Research Question



How accurately and efficiently can a Siamese CNN with few-shot learning detect signature forgeries in Sri Lankan government documents, achieving >= 92% accuracy, >= 0.95 AUC-ROC, and <= 2s inference time?



\## Methodology



\### Dataset

\- Source: CEDAR Signature Verification Dataset (Kaggle)

\- Signers: 55 (original), 30 (after signer-based split)

\- Signer-based split: 21/4/5 (train/val/test)

\- Augmented images: 2,700

\- Augmentation techniques: 7 (rotation, scale, translate, shear, brightness, noise, blur)



\### Model Architecture

\- Backbone: ResNet-18 (pretrained)

\- Embedding dimension: 128

\- Loss: Contrastive Loss (margin=1.0)

\- Optimizer: Adam (lr=1e-4)



\### Training

\- Platform: Kaggle GPU T4 x2 (DataParallel)

\- Epochs: 30

\- Batch size: 64

\- Training time: 9.3 minutes

\- Best epoch: 4

\- Best val loss: 0.1872



\## Results



\### Final Metrics



| Metric | Target | Achieved | Status |

|--------|--------|----------|--------|

| Accuracy | >= 92% | 94.75% | PASS |

| Precision | >= 90% | 93.24% | PASS |

| Recall | >= 90% | 96.50% | PASS |

| F1-Score | >= 90% | 94.84% | PASS |

| AUC-ROC | >= 0.95 | 0.9820 | PASS |

| Inference Time | <= 2s | \~0.098s | PASS |



\### 95% Confidence Interval

\- Accuracy: \[0.9211, 0.9654] (Wilson score interval)



\### Distance Distribution

\- Genuine pairs: mean=0.1072, std=0.0203

\- Forged pairs: mean=0.1637, std=0.0268

\- Separation: 0.0565



\### Statistical Significance (vs Baseline 0.85)



| Test | Value | Interpretation |

|------|-------|----------------|

| Best threshold | 0.13577 | — |

| t-statistic | 18.34 | Very high |

| p-value | 5.20 x 10^-5 | Highly significant (p << 0.001) |

| Significant at 0.05 | True | PASS |

| Cohen's d | 12.97 | Very large effect |



The extremely large Cohen's d (12.97) and very low p-value (5.20 x 10^-5) demonstrate that the Siamese CNN significantly outperforms baseline approaches with a very large effect size.



\## UI Verification



| Test | Verdict | Distance | Time |

|------|---------|----------|------|

| Genuine (signer\_11) | genuine | \~0.05 | \~100 ms |

| Forged (signer\_11) | forged | 0.1774 | 348 ms |



\## Deployment



\- \*\*API\*\*: FastAPI with `/verify` endpoint

\- \*\*Frontend\*\*: Streamlit dashboard (http://localhost:8501)

\- \*\*Documentation\*\*: Swagger UI (http://localhost:8000/docs)

\- \*\*Containerization\*\*: Docker

\- \*\*CI/CD\*\*: GitHub Actions



\## Conclusion



All RQ1 targets were met or exceeded with high statistical significance:



\- \*\*Accuracy\*\*: 94.75% (target: >= 92%)

\- \*\*Precision\*\*: 93.24% (target: >= 90%)

\- \*\*Recall\*\*: 96.50% (target: >= 90%)

\- \*\*F1\*\*: 94.84% (target: >= 90%)

\- \*\*AUC-ROC\*\*: 0.9820 (target: >= 0.95)

\- \*\*Inference\*\*: \~98 ms (target: <= 2s)

\- \*\*Statistical Significance\*\*: p = 5.20 x 10^-5 (highly significant)

\- \*\*Effect Size\*\*: Cohen's d = 12.97 (large)



The Siamese CNN with few-shot learning successfully detects signature forgeries with high accuracy and statistical confidence.

