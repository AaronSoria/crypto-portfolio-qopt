from qportfolio.solvers.base import AbstractSolver, SolverResult


class DWaveBQMSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="dwave_bqm", objective_value=0.0)
