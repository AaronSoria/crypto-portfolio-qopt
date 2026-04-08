from __future__ import annotations
from typing import Dict

def transaction_cost(dataset, fee_rate: float = 0.001) -> Dict[str, float]:
    """Simple proportional transaction cost model."""
    out: Dict[str, float] = {}
    for asset in dataset.assets:
        out[asset.symbol.upper()] = fee_rate
    return out
