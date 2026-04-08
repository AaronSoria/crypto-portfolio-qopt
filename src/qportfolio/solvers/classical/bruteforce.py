from __future__ import annotations

from qportfolio.solvers.base import AbstractSolver, SolverResult
from .common import all_binary_assignments, build_solution, evaluate_translated_problem


class BruteForceSolver(AbstractSolver):
    name = "bruteforce"

    def solve(self, translated_problem: dict) -> SolverResult:
        variables = sorted(translated_problem.get("qubo", {}).keys())
        if not variables:
            raise ValueError("BruteForceSolver expects a non-empty QUBO payload.")

        best_assignment = None
        best_value = None
        best_violations = None

        for assignment in all_binary_assignments(variables):
            value, violations = evaluate_translated_problem(translated_problem, assignment)
            if best_value is None or value < best_value:
                best_value = value
                best_assignment = assignment
                best_violations = violations

        solution = build_solution(
            translated_problem,
            best_assignment,
            best_value,
            best_violations or {},
            self.name,
            metadata={"searched_assignments": 1 << len(variables)},
        )

        return SolverResult(
            solver_name=self.name,
            objective_value=best_value,
            feasible=solution.feasible,
            solution=solution,
            metadata={"translated_type": translated_problem.get("type")},
        )
