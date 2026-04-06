from qportfolio.data.transformers import map_ohlcv_to_snapshots



def test_map_ohlcv_to_snapshots_groups_and_sorts_records() -> None:
    records = [
        {
            "symbol": "eth",
            "timestamp": "2026-01-02T00:00:00Z",
            "close": 3200.0,
            "volume": 150.0,
            "market_cap": 380000000000.0,
        },
        {
            "symbol": "btc",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 95000.0,
            "volume": 210.0,
            "market_cap": 1800000000000.0,
        },
        {
            "symbol": "eth",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 3100.0,
            "volume": 140.0,
            "market_cap": 370000000000.0,
        },
        {
            "symbol": "btc",
            "timestamp": "2026-01-02T00:00:00Z",
            "close": 96000.0,
            "volume": 220.0,
            "market_cap": 1810000000000.0,
        },
    ]

    snapshots = map_ohlcv_to_snapshots(records)

    assert len(snapshots) == 2
    assert snapshots[0].timestamp == "2026-01-01T00:00:00Z"
    assert snapshots[0].prices == {"ETH": 3100.0, "BTC": 95000.0}
    assert snapshots[0].volumes == {"ETH": 140.0, "BTC": 210.0}
    assert snapshots[0].market_caps == {
        "ETH": 370000000000.0,
        "BTC": 1800000000000.0,
    }

    assert snapshots[1].timestamp == "2026-01-02T00:00:00Z"
    assert snapshots[1].prices == {"ETH": 3200.0, "BTC": 96000.0}



def test_map_ohlcv_to_snapshots_discards_incomplete_timestamps_by_default() -> None:
    records = [
        {
            "symbol": "btc",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 95000.0,
        },
        {
            "symbol": "eth",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 3100.0,
        },
        {
            "symbol": "btc",
            "timestamp": "2026-01-02T00:00:00Z",
            "close": 96000.0,
        },
    ]

    snapshots = map_ohlcv_to_snapshots(records, asset_symbols=["BTC", "ETH"])

    assert len(snapshots) == 1
    assert snapshots[0].timestamp == "2026-01-01T00:00:00Z"



def test_map_ohlcv_to_snapshots_can_keep_partial_snapshots() -> None:
    records = [
        {
            "symbol": "btc",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 95000.0,
            "volume": 210.0,
            "market_cap": 1800000000000.0,
        },
        {
            "symbol": "eth",
            "timestamp": "2026-01-01T00:00:00Z",
            "close": 3100.0,
            "volume": 140.0,
            "market_cap": 370000000000.0,
        },
        {
            "symbol": "btc",
            "timestamp": "2026-01-02T00:00:00Z",
            "close": 96000.0,
            "volume": 220.0,
            "market_cap": 1810000000000.0,
        },
    ]

    snapshots = map_ohlcv_to_snapshots(
        records,
        asset_symbols=["BTC", "ETH"],
        require_complete_snapshots=False,
    )

    assert len(snapshots) == 2
    assert snapshots[1].timestamp == "2026-01-02T00:00:00Z"
    assert snapshots[1].prices == {"BTC": 96000.0}
    assert snapshots[1].volumes == {"BTC": 220.0}
    assert snapshots[1].market_caps == {"BTC": 1810000000000.0}
