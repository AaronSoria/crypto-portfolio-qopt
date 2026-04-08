from __future__ import annotations
from typing import Dict
import math
from qportfolio.data.preprocessing.returns import compute_log_returns

def downside_risk(dataset) -> Dict[str, float]:
    """Semi-deviation of negative log returns."""
    returns = compute_log_returns(dataset)
    out: Dict[str, float] = {}
    for k, series in returns.items():
        neg = [r for r in series if r < 0]
        n = len(neg)
        if n == 0:
            out[k] = 0.0
            continue
        mean = sum(neg)/n
        var = sum((x-mean)**2 for x in neg)/n
        out[k] = math.sqrt(var)
    return out
