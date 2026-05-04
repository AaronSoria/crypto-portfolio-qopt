"""
Classical solvers for benchmarking against quantum approaches.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from .problem import QUBOProblem


@dataclass
class ClassicalSolverResult:
    best_bitstring: str
    best_selection: List[str]
    best_energy: float
    method: str


class GreedySolver:
    """Simple greedy bit-flip local search for QUBO."""

    def __init__(self, max_iterations: int = 500, seed: int = 42):
        self.max_iterations = max_iterations
        self.seed = seed

    def solve(self, qubo: QUBOProblem) -> ClassicalSolverResult:
        rng = np.random.default_rng(self.seed)
        n = qubo.n
        x = rng.integers(0, 2, size=n).astype(float)
        best_e = qubo.evaluate(x)

        for _ in range(self.max_iterations):
            improved = False
            for i in rng.permutation(n):
                x[i] = 1 - x[i]
                e = qubo.evaluate(x)
                if e < best_e:
                    best_e = e
                    improved = True
                else:
                    x[i] = 1 - x[i]
            if not improved:
                break

        bits = "".join(str(int(xi)) for xi in x)
        selected = [qubo.symbols[i] for i, xi in enumerate(x) if xi == 1]
        return ClassicalSolverResult(
            best_bitstring=bits,
            best_selection=selected,
            best_energy=best_e,
            method="greedy_local_search",
        )


class ExactSolver:
    """Brute-force exact solver — only feasible for n ≤ 20."""

    def solve(self, qubo: QUBOProblem) -> ClassicalSolverResult:
        n = qubo.n
        if n > 20:
            raise ValueError("ExactSolver only supports n ≤ 20")
        best_e = float("inf")
        best_x = None
        for bits in itertools.product([0, 1], repeat=n):
            x = np.array(bits, dtype=float)
            e = qubo.evaluate(x)
            if e < best_e:
                best_e = e
                best_x = x.copy()
        bits = "".join(str(int(xi)) for xi in best_x)
        selected = [qubo.symbols[i] for i, xi in enumerate(best_x) if xi == 1]
        return ClassicalSolverResult(
            best_bitstring=bits,
            best_selection=selected,
            best_energy=best_e,
            method="exact_brute_force",
        )
