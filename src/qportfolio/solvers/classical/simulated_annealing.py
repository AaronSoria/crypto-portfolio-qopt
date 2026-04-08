from __future__ import annotations

import math
import random

from qportfolio.solvers.base import AbstractSolver, SolverResult
from .common import build_solution, evaluate_translated_problem, random_assignment, single_flip_neighbors


class SimulatedAnnealingSolver(AbstractSolver):
    name = "simulated_annealing"

    def __init__(self, *, iterations: int = 500, initial_temperature: float = 1.0, cooling_rate: float = 0.995, seed: int = 42) -> None:
        self.iterations = int(iterations)
        self.initial_temperature = float(initial_temperature)
        self.cooling_rate = float(cooling_rate)
        self.seed = int(seed)

    def solve(self, translated_problem: dict) -> SolverResult:
        variables = sorted(translated_problem.get("qubo", {}).keys())
        if not variables:
            raise ValueError("SimulatedAnnealingSolver expects a non-empty QUBO payload.")

        rng = random.Random(self.seed)
        current = random_assignment(variables, rng)
        current_value, current_violations = evaluate_translated_problem(translated_problem, current)

        best = dict(current)
        best_value = current_value
        best_violations = current_violations

        temperature = self.initial_temperature

        for _ in range(self.iterations):
            neighbors = list(single_flip_neighbors(current))
            candidate = neighbors[rng.randrange(len(neighbors))]
            candidate_value, candidate_violations = evaluate_translated_problem(translated_problem, candidate)

            delta = candidate_value - current_value
            accept = delta < 0.0 or rng.random() < math.exp(-delta / max(temperature, 1e-9))

            if accept:
                current = candidate
                current_value = candidate_value
                current_violations = candidate_violations

            if current_value < best_value:
                best = dict(current)
                best_value = current_value
                best_violations = current_violations

            temperature *= self.cooling_rate

        solution = build_solution(
            translated_problem,
            best,
            best_value,
            best_violations,
            self.name,
            metadata={
                "iterations": self.iterations,
                "initial_temperature": self.initial_temperature,
                "cooling_rate": self.cooling_rate,
                "seed": self.seed,
            },
        )

        return SolverResult(
            solver_name=self.name,
            objective_value=best_value,
            feasible=solution.feasible,
            solution=solution,
            metadata={"translated_type": translated_problem.get("type")},
        )
