from qportfolio.solvers.base import AbstractSolver, SolverResult


class ClassicalPresolverQuantumRefinementSolver(AbstractSolver):
    def solve(self, translated_problem: dict) -> SolverResult:
        return SolverResult(solver_name="classical_quantum_refinement", objective_value=0.0)
