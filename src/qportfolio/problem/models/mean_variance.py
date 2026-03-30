from qportfolio.problem.models.base import AbstractPortfolioProblem


class MeanVarianceBinaryProblem(AbstractPortfolioProblem):
    risk_aversion: float = 0.5

    def to_quadratic_form(self) -> dict:
        return {
            "name": self.name,
            "objective": self.objective,
            "risk_aversion": self.risk_aversion,
            "constraints": self.constraints.model_dump(),
        }
