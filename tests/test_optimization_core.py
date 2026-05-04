"""Tests for QUBO formulation and data loading."""
import numpy as np
import pytest

from qopt.data import PortfolioDataset
from qopt.problem import MeanVarianceBinaryProblem, QUBOProblem


@pytest.fixture
def dataset():
    return PortfolioDataset(
        symbols=["BTC", "ETH", "SOL"],
        expected_returns={"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
        covariance_matrix=np.array([
            [0.30, 0.10, 0.05],
            [0.10, 0.25, 0.07],
            [0.05, 0.07, 0.20],
        ]),
    )


def test_dataset_mu_vector(dataset):
    mu = dataset.mu
    assert mu.shape == (3,)
    assert mu[0] == pytest.approx(0.12)
    assert mu[1] == pytest.approx(0.08)


def test_dataset_covariance_symmetric(dataset):
    cov = dataset.covariance_matrix
    assert np.allclose(cov, cov.T)


def test_qubo_shape(dataset):
    qubo = MeanVarianceBinaryProblem(dataset, budget=2, penalty=10).build_qubo()
    assert qubo.Q.shape == (3, 3)
    assert qubo.n == 3


def test_qubo_evaluate_zero_vector(dataset):
    qubo = MeanVarianceBinaryProblem(dataset, budget=2, penalty=10).build_qubo()
    x = np.zeros(3)
    e = qubo.evaluate(x)
    assert e == pytest.approx(qubo.offset)


def test_qubo_to_ising_roundtrip(dataset):
    qubo = MeanVarianceBinaryProblem(dataset, budget=2, penalty=10).build_qubo()
    h, J, off = qubo.to_ising()
    assert h.shape == (3,)
    assert J.shape == (3, 3)
    assert isinstance(off, float)


def test_qubo_budget_penalty_enforced(dataset):
    """States with wrong budget should have higher energy than feasible states."""
    qubo = MeanVarianceBinaryProblem(dataset, budget=2, penalty=50).build_qubo()
    infeasible = np.array([1.0, 1.0, 1.0])   # k=3
    feasible   = np.array([1.0, 0.0, 1.0])   # k=2
    assert qubo.evaluate(infeasible) > qubo.evaluate(feasible)


def test_dataset_from_config():
    cfg = {
        "expected_returns": {"A": 0.05, "B": 0.10},
        "covariance_matrix": {
            "A": {"A": 0.1, "B": 0.02},
            "B": {"A": 0.02, "B": 0.2},
        },
    }
    ds = PortfolioDataset.from_config(cfg)
    assert ds.symbols == ["A", "B"]
    assert ds.n == 2
