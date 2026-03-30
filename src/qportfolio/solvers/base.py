from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class SolverConfig(BaseModel):
    family: str
    name: str
    parameters: dict = Field(default_factory=dict)


class SolverResult(BaseModel):
    solver_name: str
    objective_value: float
    feasible: bool = True
    metadata: dict = Field(default_factory=dict)


class AbstractSolver(ABC):
    config: SolverConfig

    def __init__(self, config: SolverConfig):
        self.config = config

    @abstractmethod
    def solve(self, translated_problem: dict) -> SolverResult:
        raise NotImplementedError
