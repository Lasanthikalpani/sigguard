"""First experiment: full evaluation + PostgreSQL logging (RQ1).

SigGuard - AI-Powered Signature Forgery Detection
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from eval.run_benchmark import EvaluationHarness, create_synthetic_pairs
from src.training.config import TrainingConfig
from src.db.connection import log_experiment_run, log_metrics, check_connection


def main():
    print('=' * 60)
    print('SigGuard - First Experiment (RQ1)')
    print('=' * 60)

    # 1. Check database
    print('\n[1/5] Checking database connection...')
    if check_connection():
        print('  [OK] Database connected')
    else:
        print('  [WARN] Database not available - will skip logging')

    # 2. Create synthetic data
    print('\n[2/5] Creating synthetic data...')
    pairs, signer_ids, data_dir = create_synthetic_pairs(n_signers=5)
    print(f'  Pairs: {len(pairs)}')
    print(f'  Signers: {len(set(signer_ids))}')

    # 3. Configure experiment
    print('\n[3/5] Configuring experiment...')
    config = TrainingConfig()
    config.epochs = 3
    config.backbone = 'resnet18'
    config.embedding_dim = 128

    config_dict = config.to_dict()
    print(f'  Backbone: {config.backbone}')
    print(f'  Embedding dim: {config.embedding_dim}')
    print(f'  Epochs: {config.epochs}')

    # 4. Run evaluation
    print('\n[4/5] Running evaluation...')
    harness = EvaluationHarness(
        config=config,
        n_folds=5,
        accuracy_threshold=0.92,
    )

    results = harness.run(pairs, signer_ids, verbose=True)
    harness.print_summary()
    regression_passed = harness.regression_test()

    # 5. Log to database
    print('\n[5/5] Logging results...')
    if check_connection():
        try:
            run_id = log_experiment_run(
                experiment_name='first_experiment_rq1',
                config=config_dict,
            )
            print(f'  [OK] Experiment run logged: run_id={run_id}')

            # Convert fold results to metrics list
            metrics_list = []
            n_folds = len(results['accuracy']['values'])
            for fold_idx in range(n_folds):
                metrics_list.append({
                    'accuracy': results['accuracy']['values'][fold_idx],
                    'precision': results['precision']['values'][fold_idx],
                    'recall': results['recall']['values'][fold_idx],
                    'f1': results['f1']['values'][fold_idx],
                    'auc_roc': results['auc_roc']['values'][fold_idx],
                    'inference_time': results['inference_time']['values'][fold_idx],
                })

            log_metrics(run_id, metrics_list)
            print(f'  [OK] Metrics logged ({len(metrics_list)} folds)')

            # Print summary
            print(f'\n  Best run in DB:')
            print(f'    Run ID: {run_id}')
            print(f'    Mean accuracy: {results["accuracy"]["mean"]:.4f}')
            print(f'    Mean F1: {results["f1"]["mean"]:.4f}')

        except Exception as e:
            print(f'  [ERROR] Database logging failed: {e}')
    else:
        print('  [SKIP] Database not available')

    # Final summary
    print('\n' + '=' * 60)
    print('Experiment Summary')
    print('=' * 60)
    print(f'  Accuracy: {results["accuracy"]["mean"]:.4f} '
          f'(±{results["accuracy"]["std"]:.4f})')
    print(f'  F1: {results["f1"]["mean"]:.4f} '
          f'(±{results["f1"]["std"]:.4f})')
    print(f'  AUC-ROC: {results["auc_roc"]["mean"]:.4f} '
          f'(±{results["auc_roc"]["std"]:.4f})')
    print(f'  Inference time: {results["inference_time"]["mean"]:.4f}s')
    print(f'  Regression test: {"PASS" if regression_passed else "FAIL (synthetic)"}')
    print('=' * 60)
    print('\n[OK] First experiment complete!')
    print('\nNext steps:')
    print('  - Add real signature data to data/genuine/<signer_id>/')
    print('  - Run: python src/training/train.py')
    print('  - Run: python eval/run_benchmark.py')
    print('  - View DB: docker exec -it sigguard_postgres psql -U sigguard -d sigguard')


if __name__ == '__main__':
    main()
