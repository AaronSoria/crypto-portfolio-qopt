from qportfolio.solvers.base import AbstractSolver, SolverResult


class BruteForceSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="bruteforce", objective_value=0.0)
