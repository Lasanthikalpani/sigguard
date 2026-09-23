"""Database connection and logging for SigGuard (RQ1, RQ3).

Uses PostgreSQL for experiment tracking, metrics, and audit trails.
"""
import os
import json
from contextlib import contextmanager
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


# PostgreSQL connection
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://sigguard:sigguard123@localhost:5432/sigguard'
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@contextmanager
def get_session():
    """Context manager for database sessions."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def log_experiment_run(
    experiment_name: str,
    config: dict,
    commit_hash: Optional[str] = None,
) -> int:
    """Log an experiment run and return run_id."""
    with get_session() as session:
        result = session.execute(
            text('''
                INSERT INTO experiment_runs (experiment_name, config, commit_hash)
                VALUES (:name, :config, :commit)
                RETURNING run_id
            '''),
            {
                'name': experiment_name,
                'config': json.dumps(config),
                'commit': commit_hash,
            },
        )
        return result.scalar()


def log_metrics(run_id: int, metrics_list: list) -> None:
    """Log metrics for an experiment run.

    Args:
        run_id: Experiment run ID.
        metrics_list: List of dicts with keys: accuracy, precision,
                      recall, f1, auc_roc, inference_time.
    """
    with get_session() as session:
        for fold, m in enumerate(metrics_list):
            session.execute(
                text('''
                    INSERT INTO metrics (
                        run_id, fold, accuracy, precision, recall,
                        f1, auc_roc, inference_time_ms
                    ) VALUES (
                        :run_id, :fold, :accuracy, :precision, :recall,
                        :f1, :auc_roc, :inference_time
                    )
                '''),
                {
                    'run_id': run_id,
                    'fold': fold,
                    'accuracy': m['accuracy'],
                    'precision': m['precision'],
                    'recall': m['recall'],
                    'f1': m['f1'],
                    'auc_roc': m['auc_roc'],
                    'inference_time': m['inference_time'] * 1000,
                },
            )


def get_best_run() -> dict:
    """Get the best experiment run by average accuracy."""
    with get_session() as session:
        result = session.execute(
            text('''
                SELECT
                    er.run_id,
                    er.experiment_name,
                    er.config,
                    AVG(m.accuracy) AS avg_accuracy,
                    AVG(m.inference_time_ms) AS avg_time
                FROM experiment_runs er
                JOIN metrics m ON er.run_id = m.run_id
                GROUP BY er.run_id, er.experiment_name, er.config
                ORDER BY avg_accuracy DESC
                LIMIT 1
            ''')
        ).fetchone()
        return dict(result._mapping) if result else {}


def check_connection() -> bool:
    """Check database connectivity."""
    try:
        with get_session() as session:
            session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        print(f'Database connection failed: {e}')
        return False


def get_table_names() -> list:
    """Get all table names in the database."""
    with get_session() as session:
        result = session.execute(
            text('''
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            ''')
        )
        return [row[0] for row in result]


if __name__ == '__main__':
    print('Testing database connection...')
    if check_connection():
        print('[OK] Database connected')
        print(f'[OK] Tables: {get_table_names()}')

        run_id = log_experiment_run(
            experiment_name='test_run',
            config={'backbone': 'resnet18', 'embedding_dim': 128},
        )
        print(f'[OK] Logged run: {run_id}')

        test_metrics = [
            {
                'accuracy': 0.92,
                'precision': 0.91,
                'recall': 0.90,
                'f1': 0.91,
                'auc_roc': 0.96,
                'inference_time': 1.8,
            }
        ] * 5
        log_metrics(run_id, test_metrics)
        print('[OK] Logged metrics')

        best = get_best_run()
        print(f'[OK] Best run: {best}')
    else:
        print('[FAIL] Database connection failed')
