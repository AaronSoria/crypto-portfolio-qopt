from pydantic import BaseModel, Field


class BenchmarkMetrics(BaseModel):
    total_time_seconds: float = 0.0
    compile_time_seconds: float = 0.0
    circuit_depth: int | None = None
    shots: int | None = None
    objective_value: float = 0.0
    constraint_violation: float = 0.0
    gap_to_classical: float | None = None
    execution_cost: float = 0.0
    repeatability_score: float | None = None
    extra: dict = Field(default_factory=dict)
