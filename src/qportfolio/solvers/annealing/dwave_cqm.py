from qportfolio.solvers.base import AbstractSolver, SolverResult


class DWaveCQMSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="dwave_cqm", objective_value=0.0)
