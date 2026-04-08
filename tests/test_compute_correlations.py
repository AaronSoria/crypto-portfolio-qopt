import math
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@dataclass
class Asset:
    symbol: str


@dataclass
class MarketSnapshot:
    timestamp: int
    prices: dict[str, float]
    volumes: dict[str, float]
    market_caps: dict[str, float]


@dataclass
class PortfolioDataset:
    assets: list[Asset]
    snapshots: list[MarketSnapshot]


from qportfolio.data.preprocessing.risk import correlations


def test_correlations_returns_identity_on_diagonal_for_varying_series():
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": 100.0, "ETH": 50.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": 110.0, "ETH": 55.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=3, prices={"BTC": 105.0, "ETH": 60.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=4, prices={"BTC": 120.0, "ETH": 58.0}, volumes={}, market_caps={}),
        ],
    )

    result = correlations(dataset)

    assert math.isclose(result["BTC"]["BTC"], 1.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(result["ETH"]["ETH"], 1.0, rel_tol=1e-12, abs_tol=1e-12)


def test_correlations_is_symmetric():
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": 100.0, "ETH": 80.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": 104.0, "ETH": 78.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=3, prices={"BTC": 101.0, "ETH": 81.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=4, prices={"BTC": 107.0, "ETH": 79.0}, volumes={}, market_caps={}),
        ],
    )

    result = correlations(dataset)

    assert math.isclose(result["BTC"]["ETH"], result["ETH"]["BTC"], rel_tol=1e-12, abs_tol=1e-12)


def test_correlations_returns_zero_when_volatility_is_zero():
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": 100.0, "ETH": 50.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": 100.0, "ETH": 55.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=3, prices={"BTC": 100.0, "ETH": 53.0}, volumes={}, market_caps={}),
        ],
    )

    result = correlations(dataset)

    assert result["BTC"]["BTC"] == 0.0
    assert result["BTC"]["ETH"] == 0.0
    assert result["ETH"]["BTC"] == 0.0
