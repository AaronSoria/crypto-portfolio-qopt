"""Tests for classical and Pasqal solvers."""
import numpy as np
import pytest

from qopt.data import PortfolioDataset
from qopt.problem import MeanVarianceBinaryProblem
from qopt.solver_classical import ExactSolver, GreedySolver
from qopt.solver_pasqal import PasqalNeutralAtomSolver


@pytest.fixture
def small_qubo():
    ds = PortfolioDataset(
        symbols=["BTC", "ETH", "SOL"],
        expected_returns={"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
        covariance_matrix=np.array([
            [0.30, 0.10, 0.05],
            [0.10, 0.25, 0.07],
            [0.05, 0.07, 0.20],
        ]),
    )
    return MeanVarianceBinaryProblem(ds, risk_aversion=0.5, budget=2, penalty=12.0).build_qubo()


def test_exact_solver_finds_minimum(small_qubo):
    result = ExactSolver().solve(small_qubo)
    assert result.best_energy == pytest.approx(0.08, abs=0.01)
    assert set(result.best_selection) == {"BTC", "SOL"}


def test_greedy_solver_is_feasible(small_qubo):
    result = GreedySolver(seed=42).solve(small_qubo)
    assert len(result.best_bitstring) == small_qubo.n
    assert all(c in "01" for c in result.best_bitstring)


def test_pasqal_solver_returns_result(small_qubo):
    solver = PasqalNeutralAtomSolver(n_shots=100, n_time_steps=10, use_pulser=False, seed=0)
    result = solver.solve(small_qubo)
    assert result.backend == "numpy_rydberg"
    assert result.n_shots == 100
    assert len(result.best_bitstring) == small_qubo.n
    assert isinstance(result.best_energy, float)


def test_pasqal_register_shape(small_qubo):
    solver = PasqalNeutralAtomSolver(n_shots=50, n_time_steps=5, use_pulser=False, seed=0)
    result = solver.solve(small_qubo)
    assert result.register_positions.shape == (small_qubo.n, 2)


def test_pasqal_counts_sum_to_shots(small_qubo):
    n_shots = 150
    solver = PasqalNeutralAtomSolver(n_shots=n_shots, n_time_steps=10, use_pulser=False, seed=0)
    result = solver.solve(small_qubo)
    assert sum(result.all_counts.values()) == n_shots


def test_pasqal_energy_consistent_with_qubo(small_qubo):
    solver = PasqalNeutralAtomSolver(n_shots=50, n_time_steps=5, use_pulser=False, seed=0)
    result = solver.solve(small_qubo)
    bits = result.best_bitstring
    x = np.array([int(b) for b in bits], dtype=float)
    expected = small_qubo.evaluate(x)
    assert result.best_energy == pytest.approx(expected, abs=1e-9)
