from __future__ import annotations
from typing import Dict
from qportfolio.data.preprocessing.returns import compute_log_returns

def expected_returns(dataset) -> Dict[str, float]:
    """Mean of log returns per asset."""
    returns = compute_log_returns(dataset)
    out: Dict[str, float] = {}
    for k, series in returns.items():
        if len(series) == 0:
            out[k] = 0.0
        else:
            out[k] = sum(series) / len(series)
    return out
