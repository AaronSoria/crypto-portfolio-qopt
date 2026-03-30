from abc import ABC, abstractmethod

from qportfolio.problem.models.base import AbstractPortfolioProblem


class ProblemTranslator(ABC):
    target: str

    @abstractmethod
    def translate(self, problem: AbstractPortfolioProblem) -> dict:
        raise NotImplementedError
