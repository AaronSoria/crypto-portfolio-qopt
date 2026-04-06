from __future__ import annotations

import json

from qportfolio.data.connectors import (
    load_go_portfolio_dataset,
    parse_go_portfolio_dataset,
)


def test_parse_go_portfolio_dataset_builds_complete_snapshots() -> None:
    payload = {
        "provider": "coingecko",
        "vs_currency": "usd",
        "days": 2,
        "assets": [
            {"symbol": "BTC", "provider": "coingecko", "vs_currency": "usd"},
            {"symbol": "ETH", "provider": "coingecko", "vs_currency": "usd"},
        ],
        "records": [
            {
                "symbol": "BTC",
                "timestamp": "2026-04-01T00:00:00Z",
                "open": 70000.0,
                "high": 71000.0,
                "low": 69500.0,
                "close": 70500.0,
                "volume": 1200.0,
                "market_cap": 1.4e12,
            },
            {
                "symbol": "ETH",
                "timestamp": "2026-04-01T00:00:00Z",
                "open": 3500.0,
                "high": 3600.0,
                "low": 3450.0,
                "close": 3550.0,
                "volume": 900.0,
                "market_cap": 4.1e11,
            },
            {
                "symbol": "BTC",
                "timestamp": "2026-04-02T00:00:00Z",
                "open": 70500.0,
                "high": 72000.0,
                "low": 70000.0,
                "close": 71500.0,
                "volume": 1300.0,
                "market_cap": 1.42e12,
            },
            {
                "symbol": "ETH",
                "timestamp": "2026-04-02T00:00:00Z",
                "open": 3550.0,
                "high": 3650.0,
                "low": 3525.0,
                "close": 3620.0,
                "volume": 950.0,
                "market_cap": 4.2e11,
            },
        ],
    }

    dataset = parse_go_portfolio_dataset(payload)

    assert [asset.symbol for asset in dataset.assets] == ["BTC", "ETH"]
    assert len(dataset.snapshots) == 2
    assert dataset.snapshots[0].timestamp == "2026-04-01T00:00:00Z"
    assert dataset.snapshots[0].prices == {"BTC": 70500.0, "ETH": 3550.0}
    assert dataset.snapshots[1].volumes == {"BTC": 1300.0, "ETH": 950.0}
    assert dataset.assets[0].market_cap == 1.42e12


def test_parse_go_portfolio_dataset_skips_incomplete_snapshots_by_default() -> None:
    payload = {
        "provider": "binance",
        "vs_currency": "usd",
        "days": 2,
        "assets": [
            {"symbol": "BTC", "provider": "binance", "vs_currency": "usd"},
            {"symbol": "ETH", "provider": "binance", "vs_currency": "usd"},
        ],
        "records": [
            {
                "symbol": "BTC",
                "timestamp": "2026-04-01T00:00:00Z",
                "open": 70000.0,
                "high": 71000.0,
                "low": 69500.0,
                "close": 70500.0,
                "volume": 1200.0,
                "market_cap": 1.4e12,
            },
            {
                "symbol": "BTC",
                "timestamp": "2026-04-02T00:00:00Z",
                "open": 70500.0,
                "high": 72000.0,
                "low": 70000.0,
                "close": 71500.0,
                "volume": 1300.0,
                "market_cap": 1.42e12,
            },
            {
                "symbol": "ETH",
                "timestamp": "2026-04-02T00:00:00Z",
                "open": 3550.0,
                "high": 3650.0,
                "low": 3525.0,
                "close": 3620.0,
                "volume": 950.0,
                "market_cap": 4.2e11,
            },
        ],
    }

    dataset = parse_go_portfolio_dataset(payload)

    assert len(dataset.snapshots) == 1
    assert dataset.snapshots[0].timestamp == "2026-04-02T00:00:00Z"
    assert dataset.snapshots[0].prices == {"BTC": 71500.0, "ETH": 3620.0}


def test_load_go_portfolio_dataset_reads_json_file(tmp_path) -> None:
    payload = {
        "provider": "kraken",
        "vs_currency": "usd",
        "days": 1,
        "assets": [{"symbol": "BTC", "provider": "kraken", "vs_currency": "usd"}],
        "records": [
            {
                "symbol": "BTC",
                "timestamp": "2026-04-03T00:00:00Z",
                "open": 72000.0,
                "high": 72500.0,
                "low": 71000.0,
                "close": 72250.0,
                "volume": 800.0,
                "market_cap": 1.43e12,
            }
        ],
    }

    json_path = tmp_path / "market.json"
    json_path.write_text(json.dumps(payload), encoding="utf-8")

    dataset = load_go_portfolio_dataset(json_path)

    assert len(dataset.assets) == 1
    assert dataset.assets[0].symbol == "BTC"
    assert dataset.snapshots[0].prices["BTC"] == 72250.0
