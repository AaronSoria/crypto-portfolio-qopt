from __future__ import annotations

from qportfolio.solvers.base import AbstractSolver, SolverResult
from .common import all_binary_assignments, build_solution, evaluate_translated_problem


class MILPSolver(AbstractSolver):
    name = "milp"

    def solve(self, translated_problem: dict) -> SolverResult:
        if translated_problem.get("type") not in {"qubo", "cqm"}:
            raise ValueError("MILPSolver expects a QUBO or CQM-like payload.")

        if translated_problem.get("type") == "qubo":
            variables = sorted(translated_problem.get("qubo", {}).keys())
        else:
            variables = sorted(translated_problem.get("variables", {}).keys())

        if not variables:
            raise ValueError("MILPSolver expects a non-empty payload.")

        best_assignment = None
        best_value = None
        best_violations = None

        for assignment in all_binary_assignments(variables):
            value, violations = evaluate_translated_problem(translated_problem, assignment)
            penalty = sum(violations.values()) * 1_000_000.0 if violations else 0.0
            scored_value = value + penalty

            if best_value is None or scored_value < best_value:
                best_value = scored_value
                best_assignment = assignment
                best_violations = violations

        true_value, _ = evaluate_translated_problem(translated_problem, best_assignment)
        solution = build_solution(
            translated_problem,
            best_assignment,
            true_value,
            best_violations or {},
            self.name,
            metadata={"method": "enumerative_milp_baseline"},
        )

        return SolverResult(
            solver_name=self.name,
            objective_value=true_value,
            feasible=solution.feasible,
            solution=solution,
            metadata={"translated_type": translated_problem.get("type")},
        )
