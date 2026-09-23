"""Benchmark API endpoints for RQ1."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


router = APIRouter(prefix='/benchmark', tags=['benchmark'])


class BenchmarkRequest(BaseModel):
    n_folds: int = 5
    accuracy_threshold: float = 0.92
    backbone: str = 'resnet18'
    embedding_dim: int = 128


class BenchmarkResponse(BaseModel):
    run_id: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    auc_roc: float
    passed: bool


@router.post('/run', response_model=BenchmarkResponse)
async def run_benchmark(request: BenchmarkRequest):
    """Run 5-fold CV benchmark."""
    try:
        from eval.benchmark_v2 import BenchmarkHarness
        from src.training.config import TrainingConfig
        from src.data.dataset import SignaturePairDataset
        import tempfile
        import numpy as np
        import cv2
        from pathlib import Path

        config = TrainingConfig(
            backbone=request.backbone,
            embedding_dim=request.embedding_dim,
            epochs=3,
        )

        # Build pairs with BOTH positive (label 0) and negative (label 1)
        pairs = []
        signer_ids = []

        try:
            dataset = SignaturePairDataset('data', pairs_per_epoch=50)
            signers = list(dataset.signer_ids)

            # Positive pairs (same signer, label 0)
            for signer in signers[:5]:
                images = dataset.genuine_by_signer[signer]
                if len(images) >= 2:
                    pairs.append((str(images[0]), str(images[1]), 0))
                    signer_ids.append(signer)

            # Negative pairs (different signers, label 1)
            for i in range(min(5, len(signers) - 1)):
                img1 = dataset.genuine_by_signer[signers[i]][0]
                img2 = dataset.genuine_by_signer[signers[i + 1]][0]
                pairs.append((str(img1), str(img2), 1))
                signer_ids.append(signers[i])
        except ValueError:
            pass

        # If no real pairs, use synthetic
        if len(pairs) < 4:
            tmpdir = tempfile.mkdtemp()
            data_dir = Path(tmpdir)
            for signer_idx in range(5):
                signer_dir = data_dir / 'genuine' / f'signer_{signer_idx:03d}'
                signer_dir.mkdir(parents=True)
                for sig_idx in range(3):
                    img = np.ones((300, 500), dtype=np.uint8) * 255
                    pts = np.array([
                        [50, 150 + signer_idx * 15],
                        [200, 100 + sig_idx * 20],
                        [400, 150 + signer_idx * 10],
                    ], np.int32)
                    cv2.polylines(img, [pts], False, 0, 3)
                    cv2.imwrite(str(signer_dir / f'sig_{sig_idx:03d}.png'), img)

            dataset = SignaturePairDataset(str(data_dir), pairs_per_epoch=50)
            signers = list(dataset.signer_ids)

            # Positive pairs
            for signer in signers[:5]:
                images = dataset.genuine_by_signer[signer]
                if len(images) >= 2:
                    pairs.append((str(images[0]), str(images[1]), 0))
                    signer_ids.append(signer)

            # Negative pairs
            for i in range(min(5, len(signers) - 1)):
                img1 = dataset.genuine_by_signer[signers[i]][0]
                img2 = dataset.genuine_by_signer[signers[i + 1]][0]
                pairs.append((str(img1), str(img2), 1))
                signer_ids.append(signers[i])

        harness = BenchmarkHarness(
            config=config,
            n_folds=request.n_folds,
            accuracy_threshold=request.accuracy_threshold,
        )
        results = harness.run(pairs, signer_ids, verbose=False)
        run_id = harness.log_to_db('api_benchmark')

        return BenchmarkResponse(
            run_id=run_id,
            accuracy=results['accuracy']['mean'],
            precision=results['precision']['mean'],
            recall=results['recall']['mean'],
            f1=results['f1']['mean'],
            auc_roc=results['auc_roc']['mean'],
            passed=harness.regression_test(),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get('/runs')
async def list_runs(limit: int = 10):
    """List recent benchmark runs."""
    from src.db.connection import get_session
    from sqlalchemy import text

    with get_session() as session:
        result = session.execute(
            text('''
                SELECT run_id, experiment_name, started_at
                FROM experiment_runs
                ORDER BY run_id DESC LIMIT :limit
            '''),
            {'limit': limit},
        )
        return [dict(row._mapping) for row in result]