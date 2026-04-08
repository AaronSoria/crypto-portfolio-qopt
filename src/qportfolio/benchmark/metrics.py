from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict


@dataclass(frozen=True)
class BenchmarkMetrics:
    total_runtime_seconds: float = 0.0
    compile_time_seconds: float = 0.0
    solve_time_seconds: float = 0.0
    provider_time_seconds: float = 0.0
    objective_value: float = 0.0
    feasible: bool = False
    constraint_violation: float = 0.0
    selected_asset_count: int = 0
    execution_cost: float = 0.0
    repeatability_score: float = 0.0
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
