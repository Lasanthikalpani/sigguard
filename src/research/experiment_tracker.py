"""Research infrastructure for SigGuard (RQ1).

Inspired by ML Research Engineer Job #3, #8:
- Experiment tracking with MLflow
- Hyperparameter tuning with Optuna
- Ablation studies
- Research velocity metrics
- Config management
"""
import os
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable


# ============================================================
# CONFIG MANAGEMENT
# ============================================================
class ConfigManager:
    """Manage experiment configurations."""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def save_config(self, config: Dict, name: str) -> Path:
        """Save config to JSON file."""
        config_file = self.config_dir / f"{name}.json"

        config_with_meta = {
            **config,
            "_metadata": {
                "saved_at": datetime.utcnow().isoformat(),
                "name": name,
            }
        }

        with open(config_file, 'w') as f:
            json.dump(config_with_meta, f, indent=2)

        return config_file

    def load_config(self, name: str) -> Dict:
        """Load config from JSON file."""
        config_file = self.config_dir / f"{name}.json"
        if not config_file.exists():
            raise FileNotFoundError(f"Config not found: {config_file}")

        with open(config_file, 'r') as f:
            return json.load(f)

    def list_configs(self) -> List[str]:
        """List all saved configs."""
        return [f.stem for f in self.config_dir.glob("*.json")]

    def hash_config(self, config: Dict) -> str:
        """Hash config for identification."""
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]


# ============================================================
# EXPERIMENT TRACKER
# ============================================================
class ExperimentTracker:
    """Track experiments for research velocity."""

    def __init__(self, experiment_name: str = "sigguard_rq1"):
        self.experiment_name = experiment_name
        self.experiments = []
        self.mlflow_available = self._check_mlflow()

        if self.mlflow_available:
            try:
                import mlflow
                mlflow.set_experiment(experiment_name)
                print(f"MLflow experiment: {experiment_name}")
            except Exception as e:
                print(f"MLflow error: {e}")
                self.mlflow_available = False
        else:
            print("MLflow not available - using local tracking")

        print(f"ExperimentTracker initialized")

    def _check_mlflow(self) -> bool:
        """Check if MLflow is available."""
        try:
            import mlflow
            return True
        except ImportError:
            return False

    def track_experiment(
        self,
        config: Dict,
        metrics: Dict,
        tags: Optional[Dict] = None,
        artifacts: Optional[List[str]] = None,
    ) -> str:
        """Track a single experiment."""
        experiment_id = hashlib.sha256(
            f"{time.time()}{json.dumps(config, sort_keys=True)}".encode()
        ).hexdigest()[:16]

        experiment = {
            'id': experiment_id,
            'config': config,
            'metrics': metrics,
            'tags': tags or {},
            'timestamp': datetime.utcnow().isoformat(),
        }

        if self.mlflow_available:
            try:
                import mlflow
                with mlflow.start_run(run_name=experiment_id):
                    for key, value in config.items():
                        if isinstance(value, (int, float, str, bool)):
                            mlflow.log_param(key, value)
                    for key, value in metrics.items():
                        if isinstance(value, (int, float)):
                            mlflow.log_metric(key, value)
                    if tags:
                        mlflow.set_tags(tags)
                    if artifacts:
                        for artifact in artifacts:
                            if Path(artifact).exists():
                                mlflow.log_artifact(artifact)
            except Exception as e:
                print(f"MLflow logging error: {e}")

        self.experiments.append(experiment)
        return experiment_id

    def research_velocity(self) -> Dict:
        """Calculate research velocity metrics."""
        if not self.experiments:
            return {
                'total_experiments': 0,
                'validated_experiments': 0,
                'experiments_per_hour': 0,
            }

        validated = [
            e for e in self.experiments
            if e['metrics'].get('accuracy', 0) >= 0.92
        ]

        if len(self.experiments) >= 2:
            start = datetime.fromisoformat(self.experiments[0]['timestamp'])
            end = datetime.fromisoformat(self.experiments[-1]['timestamp'])
            hours = max((end - start).total_seconds() / 3600, 0.001)
        else:
            hours = 1

        return {
            'total_experiments': len(self.experiments),
            'validated_experiments': len(validated),
            'experiments_per_hour': len(self.experiments) / hours,
            'validation_rate': len(validated) / len(self.experiments) if self.experiments else 0,
        }

    def best_experiment(self) -> Optional[Dict]:
        """Find best experiment by accuracy."""
        if not self.experiments:
            return None
        return max(
            self.experiments,
            key=lambda e: e['metrics'].get('accuracy', 0)
        )


# ============================================================
# HYPERPARAMETER TUNING
# ============================================================
class HyperparameterTuner:
    """Automated hyperparameter tuning with Optuna."""

    def __init__(self, study_name: str = "sigguard_rq1"):
        self.study_name = study_name
        self.optuna_available = self._check_optuna()

        if self.optuna_available:
            import optuna
            self.optuna = optuna
            print(f"Optuna available - study: {study_name}")
        else:
            print("Optuna not available - install: pip install optuna")

    def _check_optuna(self) -> bool:
        """Check if Optuna is available."""
        try:
            import optuna
            return True
        except ImportError:
            return False

    def suggest_config(self, trial) -> Dict:
        """Suggest hyperparameters for a trial."""
        if not self.optuna_available:
            return {}

        return {
            'margin': trial.suggest_float('margin', 0.5, 1.5),
            'embedding_dim': trial.suggest_categorical('embedding_dim', [64, 128, 256]),
            'learning_rate': trial.suggest_loguniform('learning_rate', 1e-5, 1e-3),
            'batch_size': trial.suggest_categorical('batch_size', [32, 64, 128]),
            'backbone': trial.suggest_categorical('backbone', ['resnet18', 'resnet50', 'mobilenet']),
            'weight_decay': trial.suggest_loguniform('weight_decay', 1e-6, 1e-3),
        }

    def tune(
        self,
        objective: Callable,
        n_trials: int = 50,
        direction: str = 'maximize',
    ) -> Dict:
        """Run hyperparameter tuning."""
        if not self.optuna_available:
            return {'error': 'Optuna not installed'}

        study = self.optuna.create_study(
            study_name=self.study_name,
            direction=direction,
        )

        def optuna_objective(trial):
            config = self.suggest_config(trial)
            return objective(config)

        study.optimize(optuna_objective, n_trials=n_trials)

        return {
            'best_params': study.best_params,
            'best_value': study.best_value,
            'n_trials': n_trials,
            'study_name': self.study_name,
        }


# ============================================================
# ABLATION STUDIES
# ============================================================
class AblationStudy:
    """Run ablation studies for research."""

    def __init__(self, base_config: Dict):
        self.base_config = base_config
        self.results = {}

    def run(
        self,
        variations: Dict[str, List[Any]],
        evaluate_fn: Callable,
    ) -> Dict:
        """Run ablation study."""
        for param, values in variations.items():
            self.results[param] = []

            print(f"\nAblation: {param}")
            for value in values:
                config = {**self.base_config, param: value}
                print(f"  Testing {param}={value}...")

                try:
                    metrics = evaluate_fn(config)
                    self.results[param].append({
                        'value': value,
                        'metrics': metrics,
                    })
                    print(f"    Accuracy: {metrics.get('accuracy', 'N/A')}")
                except Exception as e:
                    print(f"    Error: {e}")
                    self.results[param].append({
                        'value': value,
                        'error': str(e),
                    })

        return self.results

    def best_value(self, param: str) -> Optional[Any]:
        """Find best value for a parameter."""
        if param not in self.results:
            return None

        results = [
            r for r in self.results[param]
            if 'metrics' in r and 'accuracy' in r['metrics']
        ]

        if not results:
            return None

        best = max(results, key=lambda r: r['metrics']['accuracy'])
        return best['value']

    def summary(self) -> str:
        """Generate ablation summary."""
        lines = ["Ablation Study Summary", "=" * 60]

        for param, results in self.results.items():
            lines.append(f"\n{param}:")
            for r in results:
                if 'metrics' in r:
                    acc = r['metrics'].get('accuracy', 'N/A')
                    lines.append(f"  {r['value']}: accuracy={acc}")
                else:
                    lines.append(f"  {r['value']}: ERROR")

        return "\n".join(lines)


# ============================================================
# DATA VERSIONING
# ============================================================
class DataVersioner:
    """Lightweight data versioning."""

    def __init__(self, version_dir: str = "data/.versions"):
        self.version_dir = Path(version_dir)
        self.version_dir.mkdir(parents=True, exist_ok=True)

    def hash_directory(self, directory: str) -> str:
        """Hash directory contents."""
        hasher = hashlib.sha256()
        dir_path = Path(directory)

        for path in sorted(dir_path.rglob('*')):
            if path.is_file():
                hasher.update(path.name.encode())
                hasher.update(str(path.stat().st_size).encode())

        return hasher.hexdigest()

    def version_data(self, directory: str, name: str) -> Dict:
        """Create a data version."""
        data_hash = self.hash_directory(directory)

        version_info = {
            'name': name,
            'directory': str(directory),
            'hash': data_hash,
            'version': data_hash[:16],
            'timestamp': datetime.utcnow().isoformat(),
            'file_count': len(list(Path(directory).rglob('*.*'))),
        }

        version_file = self.version_dir / f"{name}_{data_hash[:16]}.json"
        with open(version_file, 'w') as f:
            json.dump(version_info, f, indent=2)

        return version_info

    def list_versions(self) -> List[Dict]:
        """List all data versions."""
        versions = []
        for vf in sorted(self.version_dir.glob("*.json")):
            with open(vf, 'r') as f:
                versions.append(json.load(f))
        return versions


# ============================================================
# MAIN
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("Research Infrastructure Test")
    print("=" * 60)

    # 1. Config Manager
    print("\n1. ConfigManager:")
    cm = ConfigManager("configs")
    test_config = {
        'backbone': 'resnet18',
        'embedding_dim': 128,
        'margin': 1.0,
        'learning_rate': 1e-4,
    }
    cm.save_config(test_config, "test_config")
    print(f"  Saved config: test_config")
    print(f"  Hash: {cm.hash_config(test_config)}")

    # 2. Experiment Tracker
    print("\n2. ExperimentTracker:")
    tracker = ExperimentTracker("test_experiment")
    exp_id = tracker.track_experiment(
        config=test_config,
        metrics={'accuracy': 0.9475, 'f1': 0.9484, 'auc_roc': 0.9820},
        tags={'type': 'baseline'},
    )
    print(f"  Experiment tracked: {exp_id}")
    velocity = tracker.research_velocity()
    print(f"  Research velocity: {velocity}")

    # 3. Ablation Study
    print("\n3. AblationStudy:")
    ablation = AblationStudy(base_config=test_config)

    def mock_evaluate(config):
        acc = 0.90 + 0.05 * (config['embedding_dim'] / 256)
        return {'accuracy': acc}

    results = ablation.run(
        variations={'embedding_dim': [64, 128, 256]},
        evaluate_fn=mock_evaluate,
    )
    print(ablation.summary())

    # 4. Data Versioner
    print("\n4. DataVersioner:")
    dv = DataVersioner()
    if Path('data/splits_v2').exists():
        version = dv.version_data('data/splits_v2', 'splits_v2')
        print(f"  Data version: {version['version']}")
        print(f"  File count: {version['file_count']}")

    print("\n" + "=" * 60)
    print("Research infrastructure ready")
    print("=" * 60)