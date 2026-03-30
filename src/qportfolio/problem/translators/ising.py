from qportfolio.problem.models.base import AbstractPortfolioProblem
from qportfolio.problem.translators.base import ProblemTranslator


class IsingTranslator(ProblemTranslator):
    target = "ising"

    def translate(self, problem: AbstractPortfolioProblem) -> dict:
        return {"type": self.target, "payload": problem.to_quadratic_form()}
