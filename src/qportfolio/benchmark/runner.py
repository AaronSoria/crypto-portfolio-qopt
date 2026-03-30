from pydantic import BaseModel

from qportfolio.benchmark.metrics import BenchmarkMetrics
from qportfolio.problem.models.base import ConstraintSet
from qportfolio.problem.models.mean_variance import MeanVarianceBinaryProblem
from qportfolio.problem.translators.qubo import QuboTranslator
from qportfolio.providers.local_provider import LocalSimulatorProvider
from qportfolio.solvers.base import SolverConfig
from qportfolio.solvers.classical.greedy import GreedySolver


class BenchmarkRunResult(BaseModel):
    experiment_name: str
    translated_problem_type: str
    solver_name: str
    provider_name: str
    metrics: BenchmarkMetrics


class BenchmarkRunner:
    def run_from_config(self, config: dict) -> BenchmarkRunResult:
        problem_cfg = config.get("problem", {})
        problem = MeanVarianceBinaryProblem(
            name=config.get("name", "experiment"),
            objective="mean_variance",
            risk_aversion=problem_cfg.get("risk_aversion", 0.5),
            constraints=ConstraintSet(
                budget=problem_cfg.get("budget"),
                max_weight=problem_cfg.get("max_weight"),
                long_only=problem_cfg.get("long_only", True),
            ),
        )
        translated = QuboTranslator().translate(problem)
        solver = GreedySolver(SolverConfig(family="classical", name="greedy"))
        solve_result = solver.solve(translated)
        provider = LocalSimulatorProvider()
        provider.run({"problem": translated, "solver": solve_result.model_dump()})
        return BenchmarkRunResult(
            experiment_name=config.get("name", "experiment"),
            translated_problem_type=translated["type"],
            solver_name=solve_result.solver_name,
            provider_name=provider.name,
            metrics=BenchmarkMetrics(objective_value=solve_result.objective_value),
        )
