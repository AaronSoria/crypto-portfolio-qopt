from qportfolio.problem.models.base import AbstractPortfolioProblem
from qportfolio.problem.translators.base import ProblemTranslator


class BackendNativeTranslator(ProblemTranslator):
    target = "backend_native"

    def translate(self, problem: AbstractPortfolioProblem) -> dict:
        return {"type": self.target, "payload": problem.to_quadratic_form()}
