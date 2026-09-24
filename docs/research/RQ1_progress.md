\# RQ1 Progress — 2026-09-24



\## Completed Today

\- ✅ Kaggle account created

\- ✅ Dataset uploaded to Kaggle (SigGuard Signature Data)

\- ✅ GPU T4 x2 training completed (30 epochs, 50 epochs in progress)

\- ✅ Best model: Epoch 5, Val loss 0.1926

\- ✅ Model downloaded to local: models/checkpoints/best\_model.pth

\- ✅ Manual test: Test 1 (same)=0.16, Test 2 (different)=0.36

\- ✅ Benchmark run: accuracy 0.62, AUC-ROC 0.78

\- ✅ Multi-signer pairs (109 total) — benchmark.py fix



\## Current Status

\- Model: Epoch 3, Val loss 0.2150 (downloaded)

\- Benchmark threshold: 0.25 (best for Epoch 3)

\- Best val loss: 0.1926 (Epoch 5, not available)



\## Tomorrow's Tasks

1\. Complete 50-epoch training on Kaggle

2\. Download best model (expected val loss \~0.05)

3\. Manual test with new model

4\. Benchmark with optimized threshold

5\. Update README

6\. Git push final RQ1 results



\## Commands to Resume

```powershell

\# Terminal 1: API Server

cd C:\\Users\\lasan\\Desktop\\research\\reserch\_july\_9\\sigguard

conda activate sigguard

uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000



\# Terminal 2: Benchmark

conda activate sigguard

$body = @{ n\_folds = 5 } | ConvertTo-Json

Invoke-RestMethod -Uri http://127.0.0.1:8000/benchmark/run -Method Post -Body $body -ContentType "application/json" | ConvertTo-Json

