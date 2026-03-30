from qportfolio.solvers.base import AbstractSolver, SolverResult


class WarmStartQAOASolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="warm_start_qaoa", objective_value=0.0)
