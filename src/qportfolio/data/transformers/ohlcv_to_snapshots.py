from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable, Mapping, Any

from pydantic import BaseModel, ConfigDict, Field

from qportfolio.data.schemas import MarketSnapshot


class OHLCVRecordInput(BaseModel):
    """Generic OHLCV record accepted by the snapshot mapper."""

    model_config = ConfigDict(extra="ignore")

    symbol: str
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: float = 0.0
    market_cap: float = Field(default=0.0, alias="market_cap")



def map_ohlcv_to_snapshots(
    records: Iterable[OHLCVRecordInput | Mapping[str, Any]],
    *,
    asset_symbols: list[str] | None = None,
    require_complete_snapshots: bool = True,
) -> list[MarketSnapshot]:
    """
    Transform OHLCV records into `MarketSnapshot` objects.

    Rules
    -----
    - `close` is mapped to `prices`
    - `volume` is mapped to `volumes`
    - `market_cap` is mapped to `market_caps`
    - records are grouped by timestamp and ordered ascending
    - symbols are normalized to uppercase
    - if `require_complete_snapshots=True`, only timestamps with all requested
      symbols are kept
    """

    normalized_records = [_normalize_record(record) for record in records]
    if not normalized_records:
        return []

    ordered_symbols = _resolve_asset_symbols(normalized_records, asset_symbols)
    grouped = _group_by_timestamp(normalized_records)

    snapshots: list[MarketSnapshot] = []
    for timestamp in sorted(grouped.keys()):
        by_symbol = grouped[timestamp]
        if require_complete_snapshots and not _has_full_coverage(by_symbol, ordered_symbols):
            continue

        prices: dict[str, float] = {}
        volumes: dict[str, float] = {}
        market_caps: dict[str, float] = {}

        for symbol in ordered_symbols:
            record = by_symbol.get(symbol)
            if record is None:
                continue

            prices[symbol] = float(record.close)
            volumes[symbol] = float(record.volume)
            market_caps[symbol] = float(record.market_cap)

        if prices:
            snapshots.append(
                MarketSnapshot(
                    timestamp=timestamp,
                    prices=prices,
                    volumes=volumes,
                    market_caps=market_caps,
                )
            )

    return snapshots



def _normalize_record(record: OHLCVRecordInput | Mapping[str, Any]) -> OHLCVRecordInput:
    if isinstance(record, OHLCVRecordInput):
        parsed = record
    else:
        parsed = OHLCVRecordInput.model_validate(record)

    return parsed.model_copy(update={"symbol": parsed.symbol.upper().strip()})



def _resolve_asset_symbols(
    records: list[OHLCVRecordInput],
    asset_symbols: list[str] | None,
) -> list[str]:
    if asset_symbols:
        return _unique_normalized_symbols(asset_symbols)

    return _unique_normalized_symbols(record.symbol for record in records)



def _unique_normalized_symbols(symbols: Iterable[str]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()

    for raw_symbol in symbols:
        symbol = raw_symbol.upper().strip()
        if symbol and symbol not in seen:
            ordered.append(symbol)
            seen.add(symbol)

    return ordered



def _group_by_timestamp(
    records: list[OHLCVRecordInput],
) -> dict[str, dict[str, OHLCVRecordInput]]:
    grouped: dict[str, dict[str, OHLCVRecordInput]] = defaultdict(dict)

    for record in records:
        grouped[_normalize_timestamp(record.timestamp)][record.symbol] = record

    return grouped



def _has_full_coverage(
    by_symbol: dict[str, OHLCVRecordInput],
    ordered_symbols: list[str],
) -> bool:
    return all(symbol in by_symbol for symbol in ordered_symbols)



def _normalize_timestamp(value: datetime) -> str:
    iso_value = value.isoformat()
    if iso_value.endswith("+00:00"):
        return iso_value.replace("+00:00", "Z")
    return iso_value
