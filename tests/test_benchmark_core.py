"""Tests for the benchmark pipeline."""
import pytest
from qopt.benchmark import run_benchmark


BASE_CONFIG = {
    "experiment_name": "test_benchmark",
    "seed": 0,
    "data": {"source": "in_memory"},
    "problem": {
        "risk_aversion": 0.5,
        "expected_returns": {"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
        "covariance_matrix": {
            "BTC": {"BTC": 0.30, "ETH": 0.10, "SOL": 0.05},
            "ETH": {"BTC": 0.10, "ETH": 0.25, "SOL": 0.07},
            "SOL": {"BTC": 0.05, "ETH": 0.07, "SOL": 0.20},
        },
        "constraints": {"budget": 2, "penalty": 12.0},
    },
    "solver": {"parameters": {"max_iterations": 100}},
    "pasqal": {
        "n_shots": 200,
        "n_time_steps": 20,
        "lattice_spacing_um": 10.5,
        "blockade_radius_um": 7.0,
        "use_pulser": False,
    },
}


def test_benchmark_runs():
    result = run_benchmark(BASE_CONFIG, "test_benchmark")
    assert result.experiment_name == "test_benchmark"
    assert result.symbols == ["BTC", "ETH", "SOL"]
    assert result.qubo_size == 3


def test_benchmark_finds_feasible_solution():
    result = run_benchmark(BASE_CONFIG, "test_feasible")
    budget = BASE_CONFIG["problem"]["constraints"]["budget"]
    assert len(result.pasqal["selection"]) <= budget + 1


def test_benchmark_greedy_returns_result():
    result = run_benchmark(BASE_CONFIG, "test_greedy")
    assert "selection" in result.greedy
    assert "energy" in result.greedy
    assert isinstance(result.greedy["energy"], float)


def test_benchmark_exact_optimal_computed():
    result = run_benchmark(BASE_CONFIG, "test_exact")
    assert result.optimal_energy is not None
    assert result.optimal_selection is not None


def test_benchmark_pasqal_gap_nonnegative():
    result = run_benchmark(BASE_CONFIG, "test_gap")
    if result.pasqal_vs_optimal_gap is not None:
        assert result.pasqal_vs_optimal_gap >= -1e-6
