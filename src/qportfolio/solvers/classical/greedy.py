from __future__ import annotations

from qportfolio.solvers.base import AbstractSolver, SolverResult
from .common import build_solution, evaluate_translated_problem


class GreedySolver(AbstractSolver):
    name = "greedy"

    def solve(self, translated_problem: dict) -> SolverResult:
        if translated_problem.get("type") != "qubo":
            raise ValueError("GreedySolver currently expects a QUBO payload.")

        symbols = translated_problem.get("symbols", [])
        variable_map = translated_problem.get("variable_map", {})
        qubo = translated_problem.get("qubo", {})
        constraints = translated_problem.get("metadata", {}).get("constraints", {})
        budget = constraints.get("budget")
        budget = int(budget) if budget is not None else len(symbols)

        scores = []
        for symbol in symbols:
            var = variable_map[symbol]
            diag = qubo[var].get(var, 0.0)
            scores.append((diag, symbol, var))

        scores.sort(key=lambda item: item[0])

        assignment = {var: 0 for var in qubo.keys()}
        selected = []
        for _, symbol, var in scores:
            if len(selected) >= budget:
                break
            assignment[var] = 1
            selected.append(symbol)

        objective_value, violations = evaluate_translated_problem(translated_problem, assignment)
        solution = build_solution(
            translated_problem,
            assignment,
            objective_value,
            violations,
            self.name,
            metadata={"selected_count": len(selected)},
        )

        return SolverResult(
            solver_name=self.name,
            objective_value=objective_value,
            feasible=solution.feasible,
            solution=solution,
            metadata={"translated_type": translated_problem.get("type")},
        )
