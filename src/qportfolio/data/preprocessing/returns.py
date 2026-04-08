from __future__ import annotations

import math
from typing import Dict, List


def compute_log_returns(dataset) -> Dict[str, List[float]]:
    ordered_snapshots = sorted(dataset.snapshots, key=lambda s: s.timestamp)
    symbols = [asset.symbol.upper() for asset in dataset.assets]
    out: Dict[str, List[float]] = {symbol: [] for symbol in symbols}

    if len(ordered_snapshots) < 2:
        return out

    for previous, current in zip(ordered_snapshots[:-1], ordered_snapshots[1:]):
        for symbol in symbols:
            prev_price = previous.prices.get(symbol)
            curr_price = current.prices.get(symbol)

            if prev_price is None or curr_price is None:
                continue

            if prev_price <= 0 or curr_price <= 0:
                continue

            out[symbol].append(math.log(curr_price / prev_price))

    return out
