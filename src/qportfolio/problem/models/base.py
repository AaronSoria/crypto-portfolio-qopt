from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ConstraintSet:
    budget: Optional[int] = None
    cardinality: Optional[int] = None
    min_weight: Optional[float] = None
    max_weight: Optional[float] = None
    turnover: Optional[float] = None
    long_only: bool = True
    penalty: float = 10.0
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AbstractPortfolioProblem:
    name: str
    objective: str
    constraints: ConstraintSet

    def to_quadratic_form(self) -> Dict[str, Any]:
        raise NotImplementedError
