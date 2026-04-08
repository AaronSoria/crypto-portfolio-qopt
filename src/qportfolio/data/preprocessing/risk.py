from __future__ import annotations

import math
from typing import Dict

from .returns import compute_log_returns


def covariance_matrix(dataset) -> Dict[str, Dict[str, float]]:
    returns = compute_log_returns(dataset)
    symbols = list(returns.keys())

    matrix: Dict[str, Dict[str, float]] = {
        left: {right: 0.0 for right in symbols} for left in symbols
    }

    for left in symbols:
        left_series = returns[left]
        n_left = len(left_series)

        if n_left < 2:
            continue

        mean_left = sum(left_series) / n_left

        for right in symbols:
            right_series = returns[right]

            if len(right_series) != n_left or n_left < 2:
                matrix[left][right] = 0.0
                continue

            mean_right = sum(right_series) / n_left
            numerator = sum(
                (left_series[i] - mean_left) * (right_series[i] - mean_right)
                for i in range(n_left)
            )
            matrix[left][right] = numerator / (n_left - 1)

    return matrix


def volatility(dataset) -> Dict[str, float]:
    cov = covariance_matrix(dataset)
    out: Dict[str, float] = {}

    for symbol, row in cov.items():
        variance = row.get(symbol, 0.0)
        out[symbol] = 0.0 if variance <= 0.0 else math.sqrt(variance)

    return out


def correlations(dataset) -> Dict[str, Dict[str, float]]:
    cov = covariance_matrix(dataset)
    vols = volatility(dataset)
    symbols = list(cov.keys())

    matrix: Dict[str, Dict[str, float]] = {
        left: {right: 0.0 for right in symbols} for left in symbols
    }

    for left in symbols:
        for right in symbols:
            denom = vols.get(left, 0.0) * vols.get(right, 0.0)
            matrix[left][right] = 0.0 if denom == 0.0 else cov[left][right] / denom

    return matrix
