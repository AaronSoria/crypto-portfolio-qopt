from __future__ import annotations

import math

from qportfolio.data.schemas import PortfolioDataset


# def compute_log_returns(dataset: PortfolioDataset) -> dict[str, list[float]]:
#     """Compute per-asset log returns from chronologically ordered snapshots.

#     The function only emits returns for assets present in ``dataset.assets``.
#     Snapshots are sorted by timestamp before processing. For each consecutive
#     pair of snapshots, a return is emitted when both prices are present and
#     strictly positive.
#     """

#     symbols = [asset.symbol.upper().strip() for asset in dataset.assets if asset.symbol.strip()]
#     ordered_snapshots = sorted(dataset.snapshots, key=lambda snapshot: snapshot.timestamp)

#     returns_by_symbol: dict[str, list[float]] = {symbol: [] for symbol in symbols}

#     if len(ordered_snapshots) < 2:
#         return returns_by_symbol

#     for previous, current in zip(ordered_snapshots, ordered_snapshots[1:]):
#         for symbol in symbols:
#             previous_price = _get_normalized_price(previous.prices, symbol)
#             current_price = _get_normalized_price(current.prices, symbol)

#             if previous_price is None or current_price is None:
#                 continue
#             if previous_price <= 0.0 or current_price <= 0.0:
#                 raise ValueError(
#                     f"Cannot compute log return for {symbol}: prices must be positive. "
#                     f"Got previous={previous_price}, current={current_price}."
#                 )

#             returns_by_symbol[symbol].append(math.log(current_price / previous_price))

#     return returns_by_symbol


# def _get_normalized_price(prices: dict[str, float], symbol: str) -> float | None:
#     for key, value in prices.items():
#         if key.upper().strip() == symbol:
#             return float(value)
#     return None


def compute_log_returns(dataset: PortfolioDataset) -> dict[str, list[float]]:
    snapshots = sorted(dataset.snapshots, key=lambda snapshot: snapshot.timestamp)
    symbols = [asset.symbol for asset in dataset.assets]
    result: dict[str, list[float]] = {symbol: [] for symbol in symbols}

    for previous, current in zip(snapshots, snapshots[1:]):
        for symbol in symbols:
            previous_price = previous.prices.get(symbol)
            current_price = current.prices.get(symbol)
            if previous_price is None or current_price is None:
                continue
            if previous_price <= 0 or current_price <= 0:
                continue
            result[symbol].append(math.log(current_price / previous_price))

    return result
