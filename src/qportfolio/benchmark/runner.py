from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict

from qportfolio.benchmark.metrics import BenchmarkMetrics
from qportfolio.benchmark.reports import persist_result
from qportfolio.problem.models import MeanVarianceBinaryProblem, ConstraintSet
from qportfolio.problem.translators import QuboTranslator, IsingTranslator, CQMTranslator
from qportfolio.solvers.classical import GreedySolver, BruteForceSolver, SimulatedAnnealingSolver, MILPSolver


@dataclass(frozen=True)
class BenchmarkRunResult:
    experiment_name: str
    problem_name: str
    translator_type: str
    solver_name: str
    provider_name: str
    translated_problem: Dict[str, Any]
    solver_result: Dict[str, Any]
    provider_result: Dict[str, Any]
    metrics: Dict[str, Any]
    persisted_path: str | None = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LocalSimulatorProvider:
    name = "local_simulator"

    def run(self, translated_problem: Dict[str, Any], solver_result) -> Dict[str, Any]:
        return {
            "status": "completed",
            "provider_name": self.name,
            "translated_type": translated_problem.get("type"),
            "objective_value": solver_result.objective_value,
            "feasible": solver_result.feasible,
        }


class BenchmarkRunner:
    def _build_problem(self, config: Dict[str, Any]) -> MeanVarianceBinaryProblem:
        problem_cfg = config["problem"]
        constraints_cfg = problem_cfg.get("constraints", {})

        constraint_set = ConstraintSet(
            budget=constraints_cfg.get("budget"),
            cardinality=constraints_cfg.get("cardinality"),
            min_weight=constraints_cfg.get("min_weight"),
            max_weight=constraints_cfg.get("max_weight"),
            turnover=constraints_cfg.get("turnover"),
            long_only=constraints_cfg.get("long_only", True),
            penalty=float(constraints_cfg.get("penalty", 10.0)),
            extras=constraints_cfg.get("extras", {}),
        )

        return MeanVarianceBinaryProblem(
            expected_returns=problem_cfg.get("expected_returns", {}),
            covariance_matrix=problem_cfg.get("covariance_matrix", {}),
            risk_aversion=float(problem_cfg.get("risk_aversion", 1.0)),
            constraints=constraint_set,
        )

    def _build_translator(self, config: Dict[str, Any]):
        translator_type = config["translator"]["type"].lower()
        registry = {
            "qubo": QuboTranslator,
            "ising": IsingTranslator,
            "cqm": CQMTranslator,
        }
        if translator_type not in registry:
            raise ValueError(f"Unsupported translator type: {translator_type}")
        return registry[translator_type]()

    def _build_solver(self, config: Dict[str, Any]):
        solver_cfg = config["solver"]
        solver_type = solver_cfg["type"].lower()
        parameters = solver_cfg.get("parameters", {})

        registry = {
            "greedy": lambda: GreedySolver(),
            "bruteforce": lambda: BruteForceSolver(),
            "simulated_annealing": lambda: SimulatedAnnealingSolver(**parameters),
            "milp": lambda: MILPSolver(),
        }
        if solver_type not in registry:
            raise ValueError(f"Unsupported solver type: {solver_type}")
        return registry[solver_type]()

    def _build_provider(self, config: Dict[str, Any]):
        provider_type = config["provider"]["type"].lower()
        if provider_type != "local_simulator":
            raise ValueError(f"Unsupported provider type: {provider_type}")
        return LocalSimulatorProvider()

    def run_from_config(self, config: Dict[str, Any], persist: bool = False, output_dir: str = "results/logs") -> BenchmarkRunResult:
        total_start = time.perf_counter()

        compile_start = time.perf_counter()
        problem = self._build_problem(config)
        translator = self._build_translator(config)
        translated_problem = translator.translate(problem)
        compile_time = time.perf_counter() - compile_start

        solve_start = time.perf_counter()
        solver = self._build_solver(config)
        solver_result = solver.solve(translated_problem)
        solve_time = time.perf_counter() - solve_start

        provider_start = time.perf_counter()
        provider = self._build_provider(config)
        provider_result = provider.run(translated_problem, solver_result)
        provider_time = time.perf_counter() - provider_start

        total_runtime = time.perf_counter() - total_start

        violations = solver_result.solution.constraint_violations or {}
        metrics = BenchmarkMetrics(
            total_runtime_seconds=total_runtime,
            compile_time_seconds=compile_time,
            solve_time_seconds=solve_time,
            provider_time_seconds=provider_time,
            objective_value=solver_result.objective_value,
            feasible=solver_result.feasible,
            constraint_violation=sum(float(v) for v in violations.values()),
            selected_asset_count=len(solver_result.solution.selected_assets),
            execution_cost=float(config["provider"].get("parameters", {}).get("execution_cost", 0.0)),
            repeatability_score=1.0,
            extra={
                "selected_assets": solver_result.solution.selected_assets,
                "weights": solver_result.solution.weights,
                "constraint_violations": violations,
            },
        )

        result = BenchmarkRunResult(
            experiment_name=config["experiment_name"],
            problem_name=problem.name,
            translator_type=translated_problem["type"],
            solver_name=solver_result.solver_name,
            provider_name=provider.name,
            translated_problem=translated_problem,
            solver_result=asdict(solver_result),
            provider_result=provider_result,
            metrics=metrics.to_dict(),
        )

        persisted_path = None
        if persist:
            persisted_path = persist_result(result.to_dict(), output_dir=output_dir)

        return BenchmarkRunResult(
            experiment_name=result.experiment_name,
            problem_name=result.problem_name,
            translator_type=result.translator_type,
            solver_name=result.solver_name,
            provider_name=result.provider_name,
            translated_problem=result.translated_problem,
            solver_result=result.solver_result,
            provider_result=result.provider_result,
            metrics=result.metrics,
            persisted_path=persisted_path,
            extra=result.extra,
        )
