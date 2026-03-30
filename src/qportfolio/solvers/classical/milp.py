from qportfolio.solvers.base import AbstractSolver, SolverResult


class MILPSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="milp", objective_value=0.0)
