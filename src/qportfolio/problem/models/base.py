from abc import ABC, abstractmethod
from pydantic import BaseModel, Field


class ConstraintSet(BaseModel):
    cardinality: int | None = None
    budget: float | None = None
    min_weight: float | None = None
    max_weight: float | None = None
    turnover_limit: float | None = None
    long_only: bool = True
    penalty: float = 1.0


class AbstractPortfolioProblem(BaseModel, ABC):
    name: str
    objective: str
    constraints: ConstraintSet = Field(default_factory=ConstraintSet)

    @abstractmethod
    def to_quadratic_form(self) -> dict:
        raise NotImplementedError
