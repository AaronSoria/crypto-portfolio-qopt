from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qportfolio.problem.models import MeanVarianceBinaryProblem, ConstraintSet
from qportfolio.problem.translators import QuboTranslator, CQMTranslator
from qportfolio.solvers.classical import (
    GreedySolver,
    BruteForceSolver,
    SimulatedAnnealingSolver,
    MILPSolver,
)


def _build_problem():
    return MeanVarianceBinaryProblem(
        expected_returns={"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
        covariance_matrix={
            "BTC": {"BTC": 0.30, "ETH": 0.10, "SOL": 0.05},
            "ETH": {"BTC": 0.10, "ETH": 0.25, "SOL": 0.07},
            "SOL": {"BTC": 0.05, "ETH": 0.07, "SOL": 0.20},
        },
        risk_aversion=0.5,
        constraints=ConstraintSet(budget=2, penalty=12.0),
    )


def test_greedy_solver_returns_solution_structure():
    payload = QuboTranslator().translate(_build_problem())
    result = GreedySolver().solve(payload)

    assert result.solver_name == "greedy"
    assert isinstance(result.objective_value, float)
    assert set(result.solution.assignment.keys()) == set(payload["qubo"].keys())
    assert len(result.solution.selected_assets) == 2
    assert abs(sum(result.solution.weights.values()) - 1.0) < 1e-12


def test_bruteforce_solver_finds_feasible_solution():
    payload = QuboTranslator().translate(_build_problem())
    result = BruteForceSolver().solve(payload)

    assert result.solver_name == "bruteforce"
    assert result.solution.feasible is True
    assert len(result.solution.selected_assets) == 2


def test_simulated_annealing_solver_returns_solution():
    payload = QuboTranslator().translate(_build_problem())
    result = SimulatedAnnealingSolver(iterations=200, seed=7).solve(payload)

    assert result.solver_name == "simulated_annealing"
    assert set(result.solution.assignment.keys()) == set(payload["qubo"].keys())
    assert isinstance(result.solution.objective_value, float)


def test_milp_solver_supports_qubo_and_cqm():
    qubo_payload = QuboTranslator().translate(_build_problem())
    qubo_result = MILPSolver().solve(qubo_payload)

    cqm_payload = CQMTranslator().translate(_build_problem())
    cqm_result = MILPSolver().solve(cqm_payload)

    assert qubo_result.solver_name == "milp"
    assert cqm_result.solver_name == "milp"
    assert qubo_result.solution.feasible is True
    assert cqm_result.solution.feasible is True
