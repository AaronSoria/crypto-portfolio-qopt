from __future__ import annotations

import math

from qportfolio.data.preprocessing.risk import correlations, covariance_matrix, volatility
from qportfolio.data.schemas import Asset, MarketSnapshot, PortfolioDataset


def _build_dataset() -> PortfolioDataset:
    return PortfolioDataset(
        assets=[
            Asset(symbol="BTC", name="Bitcoin"),
            Asset(symbol="ETH", name="Ethereum"),
        ],
        snapshots=[
            MarketSnapshot(timestamp="2024-01-01T00:00:00Z", prices={"BTC": 100.0, "ETH": 200.0}),
            MarketSnapshot(timestamp="2024-01-02T00:00:00Z", prices={"BTC": 110.0, "ETH": 180.0}),
            MarketSnapshot(timestamp="2024-01-03T00:00:00Z", prices={"BTC": 121.0, "ETH": 162.0}),
        ],
    )


def test_covariance_matrix_returns_dense_symmetric_matrix() -> None:
    dataset = _build_dataset()

    matrix = covariance_matrix(dataset)

    assert set(matrix.keys()) == {"BTC", "ETH"}
    assert set(matrix["BTC"].keys()) == {"BTC", "ETH"}
    assert set(matrix["ETH"].keys()) == {"BTC", "ETH"}
    assert math.isclose(matrix["BTC"]["ETH"], matrix["ETH"]["BTC"], rel_tol=1e-12, abs_tol=1e-12)



def test_covariance_and_volatility_are_zero_for_constant_log_returns() -> None:
    dataset = _build_dataset()

    matrix = covariance_matrix(dataset)
    vols = volatility(dataset)

    assert math.isclose(matrix["BTC"]["BTC"], 0.0, abs_tol=1e-12)
    assert math.isclose(matrix["ETH"]["ETH"], 0.0, abs_tol=1e-12)
    assert math.isclose(matrix["BTC"]["ETH"], 0.0, abs_tol=1e-12)
    assert math.isclose(vols["BTC"], 0.0, abs_tol=1e-12)
    assert math.isclose(vols["ETH"], 0.0, abs_tol=1e-12)



def test_correlation_is_one_for_perfectly_linear_returns() -> None:
    dataset = PortfolioDataset(
        assets=[Asset(symbol="A"), Asset(symbol="B")],
        snapshots=[
            MarketSnapshot(timestamp="2024-01-01T00:00:00Z", prices={"A": 100.0, "B": 250.0}),
            MarketSnapshot(timestamp="2024-01-02T00:00:00Z", prices={"A": 120.0, "B": 300.0}),
            MarketSnapshot(timestamp="2024-01-03T00:00:00Z", prices={"A": 132.0, "B": 330.0}),
            MarketSnapshot(timestamp="2024-01-04T00:00:00Z", prices={"A": 145.2, "B": 363.0}),
        ],
    )

    corr = correlations(dataset)

    assert math.isclose(corr["A"]["A"], 1.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(corr["B"]["B"], 1.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(corr["A"]["B"], 1.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(corr["B"]["A"], 1.0, rel_tol=1e-12, abs_tol=1e-12)



def test_correlation_defaults_to_zero_when_volatility_is_zero() -> None:
    dataset = PortfolioDataset(
        assets=[Asset(symbol="A"), Asset(symbol="B")],
        snapshots=[
            MarketSnapshot(timestamp="2024-01-01T00:00:00Z", prices={"A": 100.0, "B": 100.0}),
            MarketSnapshot(timestamp="2024-01-02T00:00:00Z", prices={"A": 110.0, "B": 100.0}),
            MarketSnapshot(timestamp="2024-01-03T00:00:00Z", prices={"A": 121.0, "B": 100.0}),
        ],
    )

    corr = correlations(dataset)

    assert math.isclose(corr["A"]["B"], 0.0, abs_tol=1e-12)
    assert math.isclose(corr["B"]["A"], 0.0, abs_tol=1e-12)
    assert math.isclose(corr["B"]["B"], 0.0, abs_tol=1e-12)
