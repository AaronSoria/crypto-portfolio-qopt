from qportfolio.solvers.base import AbstractSolver, SolverResult


class VQESolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="vqe", objective_value=0.0)
