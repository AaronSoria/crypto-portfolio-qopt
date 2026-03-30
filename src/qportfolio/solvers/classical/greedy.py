from qportfolio.solvers.base import AbstractSolver, SolverResult


class GreedySolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(
            solver_name="greedy",
            objective_value=0.0,
            metadata={"translated_type": translated_problem.get("type")},
        )
