"""RQ1 Statistical Validation."""
import numpy as np
from typing import Dict, Optional, Callable
from scipy import stats
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score,
)


class StatisticalValidator:
    """Rigorous statistical validation for RQ1."""

    def __init__(self, y_true, y_pred, y_prob, y_pred_baseline=None):
        self.y_true = np.asarray(y_true)
        self.y_pred = np.asarray(y_pred)
        self.y_prob = np.asarray(y_prob)
        self.y_pred_baseline = (
            np.asarray(y_pred_baseline) if y_pred_baseline is not None else None
        )

    def bootstrap_ci(self, metric_fn, n_bootstrap=1000, alpha=0.05, seed=42):
        rng = np.random.default_rng(seed)
        n = len(self.y_true)
        scores = []

        for _ in range(n_bootstrap):
            idx = rng.choice(n, n, replace=True)
            try:
                scores.append(metric_fn(self.y_true[idx], self.y_pred[idx]))
            except Exception:
                continue

        scores = np.array(scores)
        return {
            'mean': float(np.mean(scores)),
            'std': float(np.std(scores)),
            'ci_lower': float(np.percentile(scores, 100 * alpha / 2)),
            'ci_upper': float(np.percentile(scores, 100 * (1 - alpha / 2))),
            'confidence': 1 - alpha,
        }

    def accuracy_ci(self):
        return self.bootstrap_ci(accuracy_score)

    def precision_ci(self):
        return self.bootstrap_ci(
            lambda y, p: precision_score(y, p, zero_division=0)
        )

    def recall_ci(self):
        return self.bootstrap_ci(
            lambda y, p: recall_score(y, p, zero_division=0)
        )

    def f1_ci(self):
        return self.bootstrap_ci(
            lambda y, p: f1_score(y, p, zero_division=0)
        )

    def auc_roc_ci(self, n_bootstrap=1000, alpha=0.05, seed=42):
        """AUC-ROC confidence interval with proper bootstrap."""
        y_true = self.y_true
        y_prob = self.y_prob

        # Direct AUC-ROC
        direct_auc = roc_auc_score(y_true, y_prob)

        # If AUC < 0.5, invert
        if direct_auc < 0.5:
            y_prob = -y_prob
            direct_auc = roc_auc_score(y_true, y_prob)

        # Bootstrap
        rng = np.random.default_rng(seed)
        n = len(y_true)
        scores = []

        for _ in range(n_bootstrap):
            idx = rng.choice(n, n, replace=True)
            try:
                score = roc_auc_score(y_true[idx], y_prob[idx])
                scores.append(score)
            except Exception:
                continue

        scores = np.array(scores)

        return {
            'mean': float(np.mean(scores)),
            'std': float(np.std(scores)),
            'ci_lower': float(np.percentile(scores, 100 * alpha / 2)),
            'ci_upper': float(np.percentile(scores, 100 * (1 - alpha / 2))),
            'confidence': 1 - alpha,
            'direct_auc': float(direct_auc),
        }

    def paired_t_test(self):
        if self.y_pred_baseline is None:
            return None

        correct = (self.y_pred == self.y_true).astype(int)
        correct_baseline = (self.y_pred_baseline == self.y_true).astype(int)
        t_stat, p_value = stats.ttest_rel(correct, correct_baseline)

        return {
            'test': 'paired_t_test',
            't_statistic': float(t_stat),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
        }

    def mcnemar_test(self):
        if self.y_pred_baseline is None:
            return None

        correct = (self.y_pred == self.y_true)
        correct_baseline = (self.y_pred_baseline == self.y_true)

        a = int((correct & correct_baseline).sum())
        b = int((correct & ~correct_baseline).sum())
        c = int((~correct & correct_baseline).sum())
        d = int((~correct & ~correct_baseline).sum())

        if b + c == 0:
            return {'test': 'mcnemar', 'statistic': 0.0, 'p_value': 1.0, 'significant': False}

        statistic = (abs(b - c) - 1) ** 2 / (b + c)
        p_value = 1 - stats.chi2.cdf(statistic, df=1)

        return {
            'test': 'mcnemar',
            'statistic': float(statistic),
            'p_value': float(p_value),
            'significant': bool(p_value < 0.05),
        }

    def report(self):
        return {
            'metrics_with_ci': {
                'accuracy': self.accuracy_ci(),
                'precision': self.precision_ci(),
                'recall': self.recall_ci(),
                'f1': self.f1_ci(),
                'auc_roc': self.auc_roc_ci(),
            },
            'hypothesis_tests': {
                'paired_t_test': self.paired_t_test(),
                'mcnemar_test': self.mcnemar_test(),
            },
            'sample_size': len(self.y_true),
        }

    def print_report(self):
        report = self.report()

        print('=' * 60)
        print('RQ1 Statistical Validation Report')
        print('=' * 60)
        print(f'Sample size: {report["sample_size"]}')
        print()
        print('Metrics with 95% Confidence Intervals:')
        print('-' * 60)
        for metric, ci in report['metrics_with_ci'].items():
            print(
                f'  {metric:12s}: {ci["mean"]:.4f} '
                f'[{ci["ci_lower"]:.4f}, {ci["ci_upper"]:.4f}]'
            )

        if report['hypothesis_tests']['paired_t_test']:
            print()
            print('Hypothesis Tests:')
            print('-' * 60)
            t_test = report['hypothesis_tests']['paired_t_test']
            print(f'  Paired t-test: t={t_test["t_statistic"]:.4f}, '
                  f'p={t_test["p_value"]:.4f}')

            mcnemar = report['hypothesis_tests']['mcnemar_test']
            if mcnemar:
                print(f'  McNemar:       chi2={mcnemar["statistic"]:.4f}, '
                      f'p={mcnemar["p_value"]:.4f}')
        print('=' * 60)


if __name__ == '__main__':
    np.random.seed(42)
    n = 400
    y_true = np.random.randint(0, 2, n)
    y_prob = np.random.rand(n) * 0.7 + y_true * 0.2
    y_pred = (y_prob > 0.5).astype(int)
    y_pred_baseline = np.random.randint(0, 2, n)

    validator = StatisticalValidator(y_true, y_pred, y_prob, y_pred_baseline)
    validator.print_report()