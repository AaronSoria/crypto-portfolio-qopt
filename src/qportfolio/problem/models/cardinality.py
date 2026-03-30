from qportfolio.problem.models.base import AbstractPortfolioProblem


class CardinalityConstrainedPortfolioProblem(AbstractPortfolioProblem):
    def to_quadratic_form(self) -> dict:
        return {
            "name": self.name,
            "objective": self.objective,
            "constraints": self.constraints.model_dump(),
        }
