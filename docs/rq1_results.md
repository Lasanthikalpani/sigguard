\# RQ1: Core AI Performance



\## Research Question



How accurately and efficiently can a Siamese CNN with few-shot learning detect signature forgeries in Sri Lankan government documents, achieving >= 92% accuracy, >= 0.95 AUC-ROC, and <= 2s inference time?



\## Methodology



\### Dataset

\- Base images: 550 (55 signers x 10 signatures)

\- Augmented: 4,950 (55 signers x 90 images)

\- Signer-based split: 38/8/9 (train/val/test)

\- Augmentation: rotation, scale, translate, shear, brightness, noise, blur



\### Model Architecture

\- Backbone: ResNet-18 (pretrained)

\- Embedding dimension: 128

\- Loss: Contrastive Loss (margin=1.0)

\- Optimizer: Adam (lr=1e-4)

\- Best epoch: 4

\- Best val loss: 0.1872



\### Training

\- Platform: Kaggle GPU T4 x2 (DataParallel)

\- Epochs: 30

\- Batch size: 64

\- Training time: 9.3 minutes



\## Results (Local Verification)



| Metric | Target | Achieved | Status |

|--------|--------|----------|--------|

| Accuracy | >= 92% | 93.50% | PASS |

| Precision | >= 90% | 93.50% | PASS |

| Recall | >= 90% | 93.50% | PASS |

| F1-Score | >= 90% | 93.50% | PASS |

| AUC-ROC | >= 0.95 | 0.9718 | PASS |

| Inference Time (avg) | <= 2s | 108.69 ms | PASS |

| Inference Time (P99) | <= 2s | 220.66 ms | PASS |



\### Distance Distribution

\- Genuine pairs: mean=0.0982, std=0.0216

\- Forged pairs: mean=0.1461, std=0.0168

\- Separation: 0.0479



\### Optimal Threshold

\- Best threshold: 0.1211

\- Best F1: 0.9350



\### Test Set

\- Total pairs: 400 (200 genuine + 200 forged)

\- Source: data/splits/test (405 genuine + 405 forged images)



\## Deployment

\- API: FastAPI with /verify endpoint

\- Frontend: Streamlit dashboard

\- Documentation: Swagger UI

\- Verification: Genuine pair (0.0206), Forged pair (0.1842)



\## Conclusion



All RQ1 targets were met or exceeded. The Siamese CNN with few-shot learning successfully detects signature forgeries with 93.50% accuracy, 0.9718 AUC-ROC, and 108.69 ms inference time.

