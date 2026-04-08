from __future__ import annotations

from dataclasses import replace
from typing import Any, Callable, Optional


def _safe_call(func: Optional[Callable[..., Any]], *args, default=None, **kwargs):
    if func is None:
        return default
    return func(*args, **kwargs)


def build_full_dataset(
    dataset,
    *,
    expected_returns_fn=None,
    covariance_matrix_fn=None,
    downside_risk_fn=None,
    transaction_cost_fn=None,
    market_cap_feature_fn=None,
):
    """
    Enrich a PortfolioDataset instance with the derived quantitative features
    required by the optimization layer.

    Expected behavior:
    - computes derived fields from the already-built dataset snapshots
    - preserves the original dataset when possible
    - returns a dataset carrying:
        expected_returns
        covariance_matrix
        downside_risk
        transaction_cost
        market_cap_feature

    Notes:
    - this function is intentionally dependency-injected so the caller can wire
      the project's concrete feature implementations without introducing import
      cycles here.
    - when a function is not provided, the corresponding field falls back to an
      empty structure.
    """
    expected_returns = _safe_call(expected_returns_fn, dataset, default={}) or {}
    covariance_matrix = _safe_call(covariance_matrix_fn, dataset, default={}) or {}
    downside_risk = _safe_call(downside_risk_fn, dataset, default={}) or {}
    transaction_cost = _safe_call(transaction_cost_fn, dataset, default={}) or {}
    market_cap_feature = _safe_call(market_cap_feature_fn, dataset, default={}) or {}

    if hasattr(dataset, "__dataclass_fields__"):
        current = dataset
        for field_name, field_value in (
            ("expected_returns", expected_returns),
            ("covariance_matrix", covariance_matrix),
            ("downside_risk", downside_risk),
            ("transaction_cost", transaction_cost),
            ("market_cap_feature", market_cap_feature),
        ):
            if field_name in getattr(current, "__dataclass_fields__", {}):
                current = replace(current, **{field_name: field_value})
        return current

    setattr(dataset, "expected_returns", expected_returns)
    setattr(dataset, "covariance_matrix", covariance_matrix)
    setattr(dataset, "downside_risk", downside_risk)
    setattr(dataset, "transaction_cost", transaction_cost)
    setattr(dataset, "market_cap_feature", market_cap_feature)
    return dataset
