from dataclasses import dataclass, field
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qportfolio.data.features.market_cap import market_cap_feature
from qportfolio.data.builders.full_dataset import build_full_dataset


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
    expected_returns: dict[str, float] = field(default_factory=dict)
    covariance_matrix: dict[str, dict[str, float]] = field(default_factory=dict)
    downside_risk: dict[str, float] = field(default_factory=dict)
    transaction_cost: dict[str, float] = field(default_factory=dict)
    market_cap_feature: dict[str, float] = field(default_factory=dict)


def _build_dataset():
    return PortfolioDataset(
        assets=[Asset("BTC"), Asset("ETH")],
        snapshots=[
            MarketSnapshot(
                timestamp=1,
                prices={"BTC": 100.0, "ETH": 50.0},
                volumes={"BTC": 10.0, "ETH": 5.0},
                market_caps={"BTC": 1000.0, "ETH": 300.0},
            ),
            MarketSnapshot(
                timestamp=2,
                prices={"BTC": 110.0, "ETH": 45.0},
                volumes={"BTC": 20.0, "ETH": 10.0},
                market_caps={"BTC": 1200.0, "ETH": 350.0},
            ),
            MarketSnapshot(
                timestamp=3,
                prices={"BTC": 105.0, "ETH": 55.0},
                volumes={"BTC": 30.0, "ETH": 15.0},
                market_caps={"BTC": 1100.0, "ETH": 400.0},
            ),
        ],
    )


def test_market_cap_feature_returns_normalized_values():
    dataset = _build_dataset()
    result = market_cap_feature(dataset)

    assert set(result.keys()) == {"BTC", "ETH"}
    assert result["BTC"] == 1.0
    assert 0.0 <= result["ETH"] < 1.0


def test_market_cap_feature_can_return_raw_means():
    dataset = _build_dataset()
    result = market_cap_feature(dataset, normalize=False)

    assert result["BTC"] == 1100.0
    assert result["ETH"] == 350.0


def test_build_full_dataset_populates_derived_fields():
    dataset = _build_dataset()

    enriched = build_full_dataset(
        dataset,
        expected_returns_fn=lambda d: {"BTC": 0.01, "ETH": 0.02},
        covariance_matrix_fn=lambda d: {
            "BTC": {"BTC": 0.1, "ETH": 0.02},
            "ETH": {"BTC": 0.02, "ETH": 0.2},
        },
        downside_risk_fn=lambda d: {"BTC": 0.03, "ETH": 0.04},
        transaction_cost_fn=lambda d: {"BTC": 0.001, "ETH": 0.001},
        market_cap_feature_fn=lambda d: {"BTC": 1.0, "ETH": 0.3181818181818182},
    )

    assert enriched.expected_returns["BTC"] == 0.01
    assert enriched.covariance_matrix["ETH"]["ETH"] == 0.2
    assert enriched.downside_risk["BTC"] == 0.03
    assert enriched.transaction_cost["ETH"] == 0.001
    assert enriched.market_cap_feature["BTC"] == 1.0
