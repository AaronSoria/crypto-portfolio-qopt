from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

from qportfolio.data.schemas import MarketSnapshot, PortfolioDataset

AlignMethod = Literal["intersection", "union"]
FillMethod = Literal["none", "ffill", "zero"]


def align_time_series(
    snapshots: Iterable[MarketSnapshot],
    *,
    asset_symbols: list[str] | None = None,
    method: AlignMethod = "intersection",
    fill_method: FillMethod = "none",
    sort_timestamps: bool = True,
) -> list[MarketSnapshot]:
    """
    Align asset time series across market snapshots.

    Parameters
    ----------
    snapshots:
        Market snapshots to align.
    asset_symbols:
        Optional ordered asset universe. When omitted, it is inferred from the snapshots.
    method:
        - ``intersection`` keeps only assets present in every timestamp.
        - ``union`` keeps the full asset universe and optionally fills gaps.
    fill_method:
        Used only with ``method='union'``.
        - ``none``: keep missing values absent from the dictionaries.
        - ``ffill``: forward-fill from the last seen value per asset.
        - ``zero``: fill missing values with 0.0.
    sort_timestamps:
        Sort snapshots by timestamp before alignment.
    """

    ordered_snapshots = list(snapshots)
    if not ordered_snapshots:
        return []

    if sort_timestamps:
        ordered_snapshots = sorted(ordered_snapshots, key=lambda snapshot: snapshot.timestamp)

    universe = _resolve_asset_symbols(ordered_snapshots, asset_symbols, method)
    if not universe:
        return []

    if method == "intersection":
        return [_align_snapshot_intersection(snapshot, universe) for snapshot in ordered_snapshots]

    if method == "union":
        return _align_snapshot_union(ordered_snapshots, universe, fill_method)

    raise ValueError(f"Unsupported alignment method: {method}")



def align_dataset_time_series(
    dataset: PortfolioDataset,
    *,
    asset_symbols: list[str] | None = None,
    method: AlignMethod = "intersection",
    fill_method: FillMethod = "none",
    sort_timestamps: bool = True,
) -> PortfolioDataset:
    """Return a copy of ``PortfolioDataset`` with aligned snapshots and assets."""

    aligned_snapshots = align_time_series(
        dataset.snapshots,
        asset_symbols=asset_symbols,
        method=method,
        fill_method=fill_method,
        sort_timestamps=sort_timestamps,
    )

    final_symbols = asset_symbols or _symbols_from_snapshots(aligned_snapshots)
    normalized_symbols = [symbol.upper().strip() for symbol in final_symbols]
    allowed = set(normalized_symbols)

    aligned_assets = [
        asset
        for asset in dataset.assets
        if asset.symbol.upper().strip() in allowed
    ]
    aligned_assets.sort(key=lambda asset: normalized_symbols.index(asset.symbol.upper().strip()))

    return dataset.model_copy(
        update={
            "assets": aligned_assets,
            "snapshots": aligned_snapshots,
        }
    )



def _resolve_asset_symbols(
    snapshots: list[MarketSnapshot],
    asset_symbols: list[str] | None,
    method: AlignMethod,
) -> list[str]:
    if asset_symbols:
        return _unique_normalized(asset_symbols)

    if method == "intersection":
        common = set(snapshots[0].prices.keys())
        for snapshot in snapshots[1:]:
            common &= set(snapshot.prices.keys())
        ordered = [symbol for symbol in snapshots[0].prices.keys() if symbol in common]
        return _unique_normalized(ordered)

    return _symbols_from_snapshots(snapshots)



def _symbols_from_snapshots(snapshots: Iterable[MarketSnapshot]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for snapshot in snapshots:
        for symbol in snapshot.prices.keys():
            normalized = symbol.upper().strip()
            if normalized not in seen:
                ordered.append(normalized)
                seen.add(normalized)

    return ordered



def _unique_normalized(symbols: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for symbol in symbols:
        normalized = symbol.upper().strip()
        if normalized and normalized not in seen:
            ordered.append(normalized)
            seen.add(normalized)

    return ordered



def _align_snapshot_intersection(snapshot: MarketSnapshot, universe: list[str]) -> MarketSnapshot:
    prices = {symbol: float(snapshot.prices[symbol]) for symbol in universe}
    volumes = {
        symbol: float(snapshot.volumes[symbol])
        for symbol in universe
        if symbol in snapshot.volumes
    }
    market_caps = {
        symbol: float(snapshot.market_caps[symbol])
        for symbol in universe
        if symbol in snapshot.market_caps
    }

    return MarketSnapshot(
        timestamp=snapshot.timestamp,
        prices=prices,
        volumes=volumes,
        market_caps=market_caps,
    )



def _align_snapshot_union(
    snapshots: list[MarketSnapshot],
    universe: list[str],
    fill_method: FillMethod,
) -> list[MarketSnapshot]:
    if fill_method not in {"none", "ffill", "zero"}:
        raise ValueError(f"Unsupported fill method: {fill_method}")

    last_prices: dict[str, float] = {}
    last_volumes: dict[str, float] = {}
    last_market_caps: dict[str, float] = {}
    aligned: list[MarketSnapshot] = []

    for snapshot in snapshots:
        prices: dict[str, float] = {}
        volumes: dict[str, float] = {}
        market_caps: dict[str, float] = {}

        for symbol in universe:
            if symbol in snapshot.prices:
                prices[symbol] = float(snapshot.prices[symbol])
                last_prices[symbol] = prices[symbol]
            else:
                _maybe_fill(symbol, prices, last_prices, fill_method)

            if symbol in snapshot.volumes:
                volumes[symbol] = float(snapshot.volumes[symbol])
                last_volumes[symbol] = volumes[symbol]
            else:
                _maybe_fill(symbol, volumes, last_volumes, fill_method)

            if symbol in snapshot.market_caps:
                market_caps[symbol] = float(snapshot.market_caps[symbol])
                last_market_caps[symbol] = market_caps[symbol]
            else:
                _maybe_fill(symbol, market_caps, last_market_caps, fill_method)

        aligned.append(
            MarketSnapshot(
                timestamp=snapshot.timestamp,
                prices=prices,
                volumes=volumes,
                market_caps=market_caps,
            )
        )

    return aligned



def _maybe_fill(
    symbol: str,
    target: dict[str, float],
    last_seen: dict[str, float],
    fill_method: FillMethod,
) -> None:
    if fill_method == "zero":
        target[symbol] = 0.0
        return

    if fill_method == "ffill" and symbol in last_seen:
        target[symbol] = float(last_seen[symbol])
