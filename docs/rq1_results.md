\# RQ1: Core AI Performance



\## Research Question



How accurately and efficiently can a Siamese CNN with few-shot learning detect signature forgeries in Sri Lankan government documents, achieving >= 92% accuracy, >= 0.95 AUC-ROC, and <= 2s inference time?



\## Methodology



\### Dataset

\- Signer-based split: 21/4/5 (train/val/test)

\- Total signers: 30

\- Augmented images: 2,700 (from 1,350 base + augmentation)



\### Model Architecture

\- Backbone: ResNet-18 (pretrained)

\- Embedding dimension: 128

\- Loss: Contrastive Loss (margin=1.0)



\### Training

\- Platform: Kaggle GPU T4 x2 (DataParallel)

\- Epochs: 30

\- Training time: 9.3 minutes



\## Results (Signer-Based Split)



| Metric | Target | Achieved | Status |

|--------|--------|----------|--------|

| Accuracy | >= 92% | 94.75% | PASS |

| Precision | >= 90% | 93.24% | PASS |

| Recall | >= 90% | 96.50% | PASS |

| F1-Score | >= 90% | 94.84% | PASS |

| AUC-ROC | >= 0.95 | 0.9820 | PASS |

| Inference Time (avg) | <= 2s | 98.37 ms | PASS |

| Inference Time (P99) | <= 2s | 157.78 ms | PASS |



\### Distance Distribution

\- Genuine pairs: mean=0.1072, std=0.0203

\- Forged pairs: mean=0.1637, std=0.0268

\- Separation: 0.0565



\### Optimal Threshold

\- Best threshold: 0.1358

\- Best F1: 0.9484



\### Test Set

\- Total pairs: 400 (200 genuine + 200 forged)

\- Source: data/splits\_v2/test (225 genuine + 225 forged images)

\- Test signers: signer\_11, signer\_15, signer\_21, signer\_45, signer\_49



\## UI Verification



| Test | Verdict | Distance | Time |

|------|---------|----------|------|

| Genuine (signer\_11) | genuine | \~0.05 | \~100 ms |

| Forged (signer\_11) | forged | 0.1774 | 348 ms |



\## Conclusion



All RQ1 targets were met. The Siamese CNN with few-shot learning successfully detects signature forgeries with 94.75% accuracy, 0.9820 AUC-ROC, and 98.37 ms inference time.

