from __future__ import annotations

from typing import Dict


def market_cap_feature(dataset, normalize: bool = True) -> Dict[str, float]:
    """
    Build a per-asset market cap feature from dataset snapshots.

    Rules:
    - uses only assets declared in dataset.assets
    - aggregates market caps as the arithmetic mean across snapshots
    - ignores missing values
    - when normalize=True, scales values into [0, 1] by dividing by the max mean market cap
    """
    symbols = [asset.symbol.upper() for asset in dataset.assets]
    aggregates: Dict[str, list[float]] = {symbol: [] for symbol in symbols}

    for snapshot in dataset.snapshots:
        for symbol in symbols:
            value = snapshot.market_caps.get(symbol)
            if value is None:
                continue
            aggregates[symbol].append(float(value))

    means: Dict[str, float] = {}
    for symbol, values in aggregates.items():
        means[symbol] = (sum(values) / len(values)) if values else 0.0

    if not normalize:
        return means

    max_value = max(means.values()) if means else 0.0
    if max_value <= 0.0:
        return {symbol: 0.0 for symbol in symbols}

    return {symbol: value / max_value for symbol, value in means.items()}
