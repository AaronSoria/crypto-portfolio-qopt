from __future__ import annotations

import math

from qportfolio.data.preprocessing.returns import compute_log_returns
from qportfolio.data.schemas import PortfolioDataset


def covariance_matrix(dataset: PortfolioDataset) -> dict[str, dict[str, float]]:
    """Compute the sample covariance matrix from per-asset log returns.

    The function uses the asset order declared in ``dataset.assets`` and returns
    a dense symmetric matrix encoded as nested dictionaries.

    Notes:
    - When fewer than 2 aligned return observations are available for a pair,
      covariance defaults to ``0.0``.
    - Pairwise computation uses the common prefix of both return series. In the
      aligned dataset flow these lengths should already match.
    """
    returns = compute_log_returns(dataset)
    symbols = [asset.symbol for asset in dataset.assets]

    matrix: dict[str, dict[str, float]] = {symbol: {} for symbol in symbols}
    for left_symbol in symbols:
        for right_symbol in symbols:
            left = returns.get(left_symbol, [])
            right = returns.get(right_symbol, [])
            matrix[left_symbol][right_symbol] = _sample_covariance(left, right)
    return matrix


def volatility(dataset: PortfolioDataset) -> dict[str, float]:
    """Compute per-asset sample volatility from log returns."""
    returns = compute_log_returns(dataset)
    cov = covariance_matrix(dataset)
    result: dict[str, float] = {}

    for asset in dataset.assets:
        symbol = asset.symbol
        variance = cov.get(symbol, {}).get(symbol, 0.0)
        result[symbol] = math.sqrt(variance) if variance > 0.0 else 0.0

    return result


def correlations(dataset: PortfolioDataset) -> dict[str, dict[str, float]]:
    """Compute the Pearson correlation matrix from sample covariance values.

    If either asset has zero volatility, the pairwise correlation is set to
    ``0.0`` to avoid undefined division. Diagonal entries are ``1.0`` whenever
    the asset has positive volatility; otherwise they default to ``0.0``.
    """
    symbols = [asset.symbol for asset in dataset.assets]
    cov = covariance_matrix(dataset)
    vol = volatility(dataset)

    corr: dict[str, dict[str, float]] = {symbol: {} for symbol in symbols}
    for left_symbol in symbols:
        for right_symbol in symbols:
            denom = vol.get(left_symbol, 0.0) * vol.get(right_symbol, 0.0)
            if denom > 0.0:
                corr[left_symbol][right_symbol] = cov[left_symbol][right_symbol] / denom
            else:
                corr[left_symbol][right_symbol] = 0.0
    return corr


def _sample_covariance(left: list[float], right: list[float]) -> float:
    n = min(len(left), len(right))
    if n < 2:
        return 0.0

    left_values = left[:n]
    right_values = right[:n]

    left_mean = sum(left_values) / n
    right_mean = sum(right_values) / n

    numerator = sum(
        (left_value - left_mean) * (right_value - right_mean)
        for left_value, right_value in zip(left_values, right_values)
    )
    return numerator / (n - 1)
