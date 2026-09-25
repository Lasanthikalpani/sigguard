"""Out-of-Sample Validation Framework for RQ1."""
import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Callable, Optional
from sklearn.model_selection import StratifiedKFold, GroupKFold


class WalkForwardValidation:
    def __init__(self, n_splits=5, min_train_size=0.3):
        self.n_splits = n_splits
        self.min_train_size = min_train_size

    def split(self, n_samples, groups=None):
        splits = []
        n = n_samples
        min_train = int(n * self.min_train_size)
        for i in range(self.n_splits):
            train_end = min_train + int((n - min_train) * i / self.n_splits)
            test_start = train_end
            test_end = min(test_start + int((n - min_train) / self.n_splits), n)
            if test_start >= n:
                break
            train_indices = np.arange(0, train_end)
            test_indices = np.arange(test_start, test_end)
            splits.append((train_indices, test_indices))
        return splits


class NestedCrossValidation:
    def __init__(self, outer_splits=5, inner_splits=3, random_state=42):
        self.outer_splits = outer_splits
        self.inner_splits = inner_splits
        self.random_state = random_state

    def split(self, X, y, groups=None):
        if groups is None:
            groups = np.arange(len(X))
        groups = np.asarray(groups)
        n_groups = len(np.unique(groups))
        actual_splits = min(self.outer_splits, n_groups)
        print(f'  NestedCV: {n_groups} groups, using {actual_splits} splits')

        if actual_splits < 2:
            print(f'  Fallback: using StratifiedKFold(2)')
            skf = StratifiedKFold(n_splits=2, shuffle=True, random_state=self.random_state)
            result = []
            for train_idx, test_idx in skf.split(X, y):
                result.append({'train': train_idx, 'test': test_idx, 'inner_splits': []})
            return result

        outer_cv = GroupKFold(n_splits=actual_splits)
        outer_splits_list = []
        for train_idx, test_idx in outer_cv.split(X, y, groups):
            n_inner = min(self.inner_splits, len(np.unique(y[train_idx])))
            inner_splits_list = []
            if n_inner >= 2:
                inner_cv = StratifiedKFold(n_splits=n_inner, shuffle=True, random_state=self.random_state)
                try:
                    for inner_train_idx, inner_val_idx in inner_cv.split(X[train_idx], y[train_idx]):
                        inner_train = train_idx[inner_train_idx]
                        inner_val = train_idx[inner_val_idx]
                        inner_splits_list.append((inner_train, inner_val))
                except Exception:
                    inner_splits_list = []
            outer_splits_list.append({
                'train': train_idx,
                'test': test_idx,
                'inner_splits': inner_splits_list,
            })
        return outer_splits_list


class PurgedKFold:
    def __init__(self, n_splits=5, purge_gap=5, embargo_pct=0.01):
        self.n_splits = n_splits
        self.purge_gap = purge_gap
        self.embargo_pct = embargo_pct

    def split(self, X, y, groups=None):
        n = len(X)
        indices = np.arange(n)
        actual_splits = min(self.n_splits, max(2, n // 10))
        print(f'  PurgedKFold: {n} samples, using {actual_splits} splits')
        test_size = max(1, n // actual_splits)
        embargo = int(n * self.embargo_pct)
        splits = []
        for i in range(actual_splits):
            test_start = i * test_size
            test_end = min((i + 1) * test_size, n)
            if test_start >= n:
                break
            test_indices = indices[test_start:test_end]
            train_mask = np.ones(n, dtype=bool)
            train_mask[test_start:test_end] = False
            purge_start = max(0, test_start - self.purge_gap)
            train_mask[purge_start:test_start] = False
            purge_end = min(n, test_end + self.purge_gap)
            train_mask[test_end:purge_end] = False
            embargo_end = min(n, test_end + embargo)
            train_mask[test_end:embargo_end] = False
            train_indices = indices[train_mask]
            if len(train_indices) > 0 and len(test_indices) > 0:
                splits.append((train_indices, test_indices))
        return splits


class OutOfSampleEvaluator:
    def __init__(self, random_state=42):
        self.random_state = random_state
        self.results = {}

    def evaluate_all(self, X, y, groups, evaluate_fn):
        print('=' * 60)
        print('OUT-OF-SAMPLE VALIDATION')
        print('=' * 60)
        print()
        print(f'Data: {len(X)} samples, {len(np.unique(groups))} groups')
        print()

        print('[1/4] Walk-forward validation...')
        wf = WalkForwardValidation(n_splits=5)
        wf_splits = wf.split(len(X), groups)
        print(f'  Splits: {len(wf_splits)}')
        wf_results = self._run_splits(wf_splits, X, y, evaluate_fn)
        self.results['walk_forward'] = wf_results
        print(f'  Accuracy: {wf_results["mean_accuracy"]:.4f} +/- {wf_results["std_accuracy"]:.4f}')
        print()

        print('[2/4] Nested cross-validation...')
        nc = NestedCrossValidation(outer_splits=5, inner_splits=3)
        nc_splits = nc.split(X, y, groups)
        print(f'  Splits: {len(nc_splits)}')
        nc_results = self._run_nested_splits(nc_splits, X, y, evaluate_fn)
        self.results['nested_cv'] = nc_results
        print(f'  Accuracy: {nc_results["mean_accuracy"]:.4f} +/- {nc_results["std_accuracy"]:.4f}')
        print()

        print('[3/4] Purged K-fold...')
        pk = PurgedKFold(n_splits=5, purge_gap=5)
        pk_splits = pk.split(X, y, groups)
        print(f'  Splits: {len(pk_splits)}')
        pk_results = self._run_splits(pk_splits, X, y, evaluate_fn)
        self.results['purged_kfold'] = pk_results
        print(f'  Accuracy: {pk_results["mean_accuracy"]:.4f} +/- {pk_results["std_accuracy"]:.4f}')
        print()

        print('[4/4] Standard 5-fold CV (baseline)...')
        skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=self.random_state)
        sk_splits = list(skf.split(X, y))
        print(f'  Splits: {len(sk_splits)}')
        sk_results = self._run_splits(sk_splits, X, y, evaluate_fn)
        self.results['standard_kfold'] = sk_results
        print(f'  Accuracy: {sk_results["mean_accuracy"]:.4f} +/- {sk_results["std_accuracy"]:.4f}')
        print()

        print('=' * 60)
        print('SUMMARY')
        print('=' * 60)
        for method, result in self.results.items():
            print(f'{method:20s}: {result["mean_accuracy"]:.4f} +/- {result["std_accuracy"]:.4f}')

        return self.results

    def _run_splits(self, splits, X, y, evaluate_fn):
        accuracies = []
        for train_idx, test_idx in splits:
            X_train, y_train = X[train_idx], y[train_idx]
            X_test, y_test = X[test_idx], y[test_idx]
            try:
                metrics = evaluate_fn(X_train, y_train, X_test, y_test)
                accuracies.append(metrics['accuracy'])
            except Exception as e:
                print(f'  Error: {e}')
        return {
            'n_splits': len(splits),
            'accuracies': accuracies,
            'mean_accuracy': float(np.mean(accuracies)) if accuracies else 0,
            'std_accuracy': float(np.std(accuracies)) if accuracies else 0,
            'min_accuracy': float(np.min(accuracies)) if accuracies else 0,
            'max_accuracy': float(np.max(accuracies)) if accuracies else 0,
        }

    def _run_nested_splits(self, splits, X, y, evaluate_fn):
        accuracies = []
        for split in splits:
            X_train = X[split['train']]
            y_train = y[split['train']]
            X_test = X[split['test']]
            y_test = y[split['test']]
            try:
                metrics = evaluate_fn(X_train, y_train, X_test, y_test)
                accuracies.append(metrics['accuracy'])
            except Exception as e:
                print(f'  Error: {e}')
        return {
            'n_splits': len(splits),
            'accuracies': accuracies,
            'mean_accuracy': float(np.mean(accuracies)) if accuracies else 0,
            'std_accuracy': float(np.std(accuracies)) if accuracies else 0,
            'min_accuracy': float(np.min(accuracies)) if accuracies else 0,
            'max_accuracy': float(np.max(accuracies)) if accuracies else 0,
        }
