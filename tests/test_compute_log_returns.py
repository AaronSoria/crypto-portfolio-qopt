import math

import pytest

from qportfolio.data.preprocessing.returns import compute_log_returns
from qportfolio.data.schemas import Asset, MarketSnapshot, PortfolioDataset


def test_compute_log_returns_for_aligned_snapshots() -> None:
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        snapshots=[
            MarketSnapshot(
                timestamp="2025-01-01T00:00:00Z",
                prices={"BTC": 100.0, "ETH": 50.0},
            ),
            MarketSnapshot(
                timestamp="2025-01-02T00:00:00Z",
                prices={"BTC": 110.0, "ETH": 55.0},
            ),
            MarketSnapshot(
                timestamp="2025-01-03T00:00:00Z",
                prices={"BTC": 121.0, "ETH": 49.5},
            ),
        ],
    )

    result = compute_log_returns(dataset)

    assert result["BTC"] == pytest.approx([math.log(1.1), math.log(1.1)])
    assert result["ETH"] == pytest.approx([math.log(1.1), math.log(0.9)])


def test_compute_log_returns_sorts_snapshots_and_skips_missing_prices() -> None:
    dataset = PortfolioDataset(
        assets=[Asset(symbol="btc"), Asset(symbol="eth")],
        snapshots=[
            MarketSnapshot(
                timestamp="2025-01-03T00:00:00Z",
                prices={"BTC": 121.0, "ETH": 49.5},
            ),
            MarketSnapshot(
                timestamp="2025-01-01T00:00:00Z",
                prices={"BTC": 100.0, "ETH": 50.0},
            ),
            MarketSnapshot(
                timestamp="2025-01-02T00:00:00Z",
                prices={"BTC": 110.0},
            ),
        ],
    )

    result = compute_log_returns(dataset)

    assert result["BTC"] == pytest.approx([math.log(1.1), math.log(1.1)])
    assert result["ETH"] == []


def test_compute_log_returns_rejects_non_positive_prices() -> None:
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC")],
        snapshots=[
            MarketSnapshot(timestamp="2025-01-01T00:00:00Z", prices={"BTC": 100.0}),
            MarketSnapshot(timestamp="2025-01-02T00:00:00Z", prices={"BTC": 0.0}),
        ],
    )

    with pytest.raises(ValueError, match="prices must be positive"):
        compute_log_returns(dataset)
