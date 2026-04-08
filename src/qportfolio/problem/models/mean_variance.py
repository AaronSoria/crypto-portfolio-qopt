from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from base import AbstractPortfolioProblem, ConstraintSet


@dataclass(frozen=True)
class MeanVarianceBinaryProblem(AbstractPortfolioProblem):
    expected_returns: Dict[str, float]
    covariance_matrix: Dict[str, Dict[str, float]]
    risk_aversion: float = 1.0

    def __init__(
        self,
        *,
        expected_returns: Dict[str, float],
        covariance_matrix: Dict[str, Dict[str, float]],
        risk_aversion: float = 1.0,
        constraints: ConstraintSet | None = None,
        name: str = "mean_variance_binary",
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "objective", "maximize_return_minimize_risk")
        object.__setattr__(self, "constraints", constraints or ConstraintSet())
        object.__setattr__(self, "expected_returns", {k.upper(): float(v) for k, v in expected_returns.items()})
        normalized_cov = {
            left.upper(): {right.upper(): float(value) for right, value in row.items()}
            for left, row in covariance_matrix.items()
        }
        object.__setattr__(self, "covariance_matrix", normalized_cov)
        object.__setattr__(self, "risk_aversion", float(risk_aversion))

    def asset_symbols(self) -> list[str]:
        symbols = set(self.expected_returns.keys())
        for left, row in self.covariance_matrix.items():
            symbols.add(left)
            symbols.update(row.keys())
        return sorted(symbols)

    def to_quadratic_form(self) -> Dict[str, Any]:
        symbols = self.asset_symbols()

        linear: Dict[str, float] = {}
        quadratic: Dict[str, Dict[str, float]] = {
            left: {right: 0.0 for right in symbols} for left in symbols
        }

        # Objective:
        # maximize mu^T x - lambda * x^T Sigma x
        # equivalent minimization:
        # minimize -mu^T x + lambda * x^T Sigma x
        for symbol in symbols:
            linear[symbol] = -float(self.expected_returns.get(symbol, 0.0))

        for left in symbols:
            row = self.covariance_matrix.get(left, {})
            for right in symbols:
                quadratic[left][right] = self.risk_aversion * float(row.get(right, 0.0))

        return {
            "name": self.name,
            "objective": self.objective,
            "symbols": symbols,
            "linear": linear,
            "quadratic": quadratic,
            "risk_aversion": self.risk_aversion,
            "constraints": {
                "budget": self.constraints.budget,
                "cardinality": self.constraints.cardinality,
                "min_weight": self.constraints.min_weight,
                "max_weight": self.constraints.max_weight,
                "turnover": self.constraints.turnover,
                "long_only": self.constraints.long_only,
                "penalty": self.constraints.penalty,
                "extras": self.constraints.extras,
            },
        }
