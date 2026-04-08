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


from qportfolio.data.preprocessing.risk import volatility


def test_volatility_returns_positive_values_for_varying_prices():
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC"), Asset(symbol="ETH")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": 100.0, "ETH": 50.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": 110.0, "ETH": 55.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=3, prices={"BTC": 105.0, "ETH": 60.0}, volumes={}, market_caps={}),
        ],
    )

    result = volatility(dataset)

    assert set(result.keys()) == {"BTC", "ETH"}
    assert result["BTC"] > 0.0
    assert result["ETH"] > 0.0


def test_volatility_returns_zero_when_not_enough_observations():
    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": 100.0}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": 101.0}, volumes={}, market_caps={}),
        ],
    )

    result = volatility(dataset)

    assert result["BTC"] == 0.0


def test_volatility_matches_sqrt_of_sample_variance_of_log_returns():
    p1, p2, p3 = 100.0, 110.0, 121.0
    r1 = math.log(p2 / p1)
    r2 = math.log(p3 / p2)

    mean = (r1 + r2) / 2.0
    expected_variance = ((r1 - mean) ** 2 + (r2 - mean) ** 2) / (2 - 1)
    expected_volatility = math.sqrt(expected_variance)

    dataset = PortfolioDataset(
        assets=[Asset(symbol="BTC")],
        snapshots=[
            MarketSnapshot(timestamp=1, prices={"BTC": p1}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=2, prices={"BTC": p2}, volumes={}, market_caps={}),
            MarketSnapshot(timestamp=3, prices={"BTC": p3}, volumes={}, market_caps={}),
        ],
    )

    result = volatility(dataset)

    assert math.isclose(result["BTC"], expected_volatility, rel_tol=1e-12, abs_tol=1e-12)
