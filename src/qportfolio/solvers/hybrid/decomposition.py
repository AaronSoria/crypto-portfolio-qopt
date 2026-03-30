from qportfolio.solvers.base import AbstractSolver, SolverResult


class DecompositionStitchingSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="decomposition_stitching", objective_value=0.0)
