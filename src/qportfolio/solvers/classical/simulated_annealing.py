from qportfolio.solvers.base import AbstractSolver, SolverResult


class SimulatedAnnealingSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="simulated_annealing", objective_value=0.0)
