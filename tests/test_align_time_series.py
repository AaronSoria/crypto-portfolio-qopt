from qportfolio.data.schemas import Asset, MarketSnapshot, PortfolioDataset
from qportfolio.data.preprocessing import align_dataset_time_series, align_time_series



def test_align_time_series_intersection_keeps_only_common_assets() -> None:
    snapshots = [
        MarketSnapshot(
            timestamp="2026-01-02T00:00:00Z",
            prices={"BTC": 96000.0, "ETH": 3200.0},
            volumes={"BTC": 220.0, "ETH": 150.0},
            market_caps={"BTC": 1810000000000.0, "ETH": 380000000000.0},
        ),
        MarketSnapshot(
            timestamp="2026-01-01T00:00:00Z",
            prices={"BTC": 95000.0, "ETH": 3100.0, "SOL": 190.0},
            volumes={"BTC": 210.0, "ETH": 140.0, "SOL": 99.0},
            market_caps={"BTC": 1800000000000.0, "ETH": 370000000000.0, "SOL": 90000000000.0},
        ),
    ]

    aligned = align_time_series(snapshots, method="intersection")

    assert [snapshot.timestamp for snapshot in aligned] == [
        "2026-01-01T00:00:00Z",
        "2026-01-02T00:00:00Z",
    ]
    assert aligned[0].prices == {"BTC": 95000.0, "ETH": 3100.0}
    assert aligned[1].prices == {"BTC": 96000.0, "ETH": 3200.0}
    assert "SOL" not in aligned[0].prices
    assert "SOL" not in aligned[1].prices



def test_align_time_series_union_with_forward_fill_keeps_universe() -> None:
    snapshots = [
        MarketSnapshot(
            timestamp="2026-01-01T00:00:00Z",
            prices={"BTC": 95000.0, "ETH": 3100.0},
            volumes={"BTC": 210.0, "ETH": 140.0},
            market_caps={"BTC": 1800000000000.0, "ETH": 370000000000.0},
        ),
        MarketSnapshot(
            timestamp="2026-01-02T00:00:00Z",
            prices={"BTC": 96000.0},
            volumes={"BTC": 220.0},
            market_caps={"BTC": 1810000000000.0},
        ),
    ]

    aligned = align_time_series(
        snapshots,
        asset_symbols=["BTC", "ETH"],
        method="union",
        fill_method="ffill",
    )

    assert aligned[1].prices == {"BTC": 96000.0, "ETH": 3100.0}
    assert aligned[1].volumes == {"BTC": 220.0, "ETH": 140.0}
    assert aligned[1].market_caps == {"BTC": 1810000000000.0, "ETH": 370000000000.0}



def test_align_dataset_time_series_filters_assets_to_aligned_universe() -> None:
    dataset = PortfolioDataset(
        assets=[
            Asset(symbol="BTC", name="Bitcoin"),
            Asset(symbol="ETH", name="Ethereum"),
            Asset(symbol="SOL", name="Solana"),
        ],
        snapshots=[
            MarketSnapshot(
                timestamp="2026-01-01T00:00:00Z",
                prices={"BTC": 95000.0, "ETH": 3100.0, "SOL": 190.0},
                volumes={"BTC": 210.0, "ETH": 140.0, "SOL": 99.0},
                market_caps={"BTC": 1800000000000.0, "ETH": 370000000000.0, "SOL": 90000000000.0},
            ),
            MarketSnapshot(
                timestamp="2026-01-02T00:00:00Z",
                prices={"BTC": 96000.0, "ETH": 3200.0},
                volumes={"BTC": 220.0, "ETH": 150.0},
                market_caps={"BTC": 1810000000000.0, "ETH": 380000000000.0},
            ),
        ],
    )

    aligned = align_dataset_time_series(dataset, method="intersection")

    assert [asset.symbol for asset in aligned.assets] == ["BTC", "ETH"]
    assert all(set(snapshot.prices.keys()) == {"BTC", "ETH"} for snapshot in aligned.snapshots)



def test_align_time_series_union_with_zero_fill_fills_missing_values() -> None:
    snapshots = [
        MarketSnapshot(
            timestamp="2026-01-01T00:00:00Z",
            prices={"BTC": 95000.0},
            volumes={"BTC": 210.0},
            market_caps={"BTC": 1800000000000.0},
        ),
        MarketSnapshot(
            timestamp="2026-01-02T00:00:00Z",
            prices={"ETH": 3200.0},
            volumes={"ETH": 150.0},
            market_caps={"ETH": 380000000000.0},
        ),
    ]

    aligned = align_time_series(
        snapshots,
        asset_symbols=["BTC", "ETH"],
        method="union",
        fill_method="zero",
    )

    assert aligned[0].prices == {"BTC": 95000.0, "ETH": 0.0}
    assert aligned[1].prices == {"BTC": 0.0, "ETH": 3200.0}
