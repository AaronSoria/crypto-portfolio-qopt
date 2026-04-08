from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class SolverConfig:
    family: str
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PortfolioSolution:
    selected_assets: List[str]
    assignment: Dict[str, int]
    weights: Dict[str, float]
    objective_value: float
    feasible: bool
    constraint_violations: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SolverResult:
    solver_name: str
    objective_value: float
    feasible: bool
    solution: PortfolioSolution
    metadata: Dict[str, Any] = field(default_factory=dict)


class AbstractSolver:
    name: str = "abstract"

    def solve(self, translated_problem: dict) -> SolverResult:
        raise NotImplementedError
