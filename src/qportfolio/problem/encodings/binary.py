from __future__ import annotations

from typing import Dict, List


def binary_asset_selection(symbols_or_count) -> List[str]:
    if isinstance(symbols_or_count, int):
        return [f"x_{index}" for index in range(symbols_or_count)]

    symbols = [str(symbol).upper() for symbol in symbols_or_count]
    return [f"x_{symbol}" for symbol in symbols]


def binary_encoding_map(symbols: list[str]) -> Dict[str, str]:
    normalized = [symbol.upper() for symbol in symbols]
    return {symbol: f"x_{symbol}" for symbol in normalized}


def inverse_binary_encoding_map(symbols: list[str]) -> Dict[str, str]:
    mapping = binary_encoding_map(symbols)
    return {variable: symbol for symbol, variable in mapping.items()}
