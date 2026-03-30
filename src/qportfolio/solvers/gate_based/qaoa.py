from qportfolio.solvers.base import AbstractSolver, SolverResult


class QAOASolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="qaoa", objective_value=0.0)
