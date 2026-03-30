from qportfolio.solvers.base import AbstractSolver, SolverResult


class SamplingHeuristicSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="sampling_heuristic", objective_value=0.0)
