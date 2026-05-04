"""
Problem formulations for portfolio optimisation.

Translates abstract problems to:
  - QUBO  (Q matrix + offset)
  - Ising (h vector + J matrix)
  - Native Pasqal (MIS / MaxCut on register geometry)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Tuple

import numpy as np

from .data import PortfolioDataset


@dataclass
class QUBOProblem:
    """Binary quadratic model: minimise  x^T Q x  subject to  x ∈ {0,1}^n."""
    Q: np.ndarray          # (n x n) upper-triangular QUBO matrix
    offset: float          # constant term
    symbols: list
    meta: dict             # problem metadata for reporting

    @property
    def n(self):
        return len(self.symbols)

    def to_ising(self) -> Tuple[np.ndarray, np.ndarray, float]:
        """
        Convert QUBO to Ising.
        x_i = (1 - s_i) / 2   where  s_i ∈ {-1, +1}
        Returns (h, J, offset_ising)
        """
        Q = (self.Q + self.Q.T) / 2          # symmetrise
        n = self.n
        h = np.zeros(n)
        J = np.zeros((n, n))
        offset_ising = self.offset

        for i in range(n):
            h[i] = Q[i, i] / 2 + sum(Q[i, j] / 4 for j in range(n) if j != i)
            offset_ising += Q[i, i] / 4
            for j in range(i + 1, n):
                J[i, j] = Q[i, j] / 4
                h[i] += Q[i, j] / 4
                h[j] += Q[i, j] / 4
                offset_ising += Q[i, j] / 4

        return h, J, offset_ising

    def evaluate(self, x: np.ndarray) -> float:
        """Evaluate QUBO objective for binary vector x."""
        return float(x @ self.Q @ x) + self.offset


class MeanVarianceBinaryProblem:
    """
    Markowitz mean-variance portfolio selection encoded as a QUBO.

    Objective (minimise):
        -sum_i mu_i x_i  +  lambda * sum_{ij} Sigma_{ij} x_i x_j
        + P * (sum_i x_i - K)^2

    Where:
        mu_i       = expected return of asset i
        Sigma_{ij} = covariance
        lambda     = risk aversion coefficient
        K          = budget (number of assets to select)
        P          = penalty coefficient for budget constraint
    """

    def __init__(
        self,
        dataset: PortfolioDataset,
        risk_aversion: float = 0.5,
        budget: int = 2,
        penalty: float = 10.0,
    ):
        self.dataset = dataset
        self.risk_aversion = risk_aversion
        self.budget = budget
        self.penalty = penalty

    def build_qubo(self) -> QUBOProblem:
        n = self.dataset.n
        mu = self.dataset.mu
        Sigma = self.dataset.covariance_matrix
        lam = self.risk_aversion
        P = self.penalty
        K = self.budget

        Q = np.zeros((n, n))

        # Return terms (diagonal)
        for i in range(n):
            Q[i, i] -= mu[i]

        # Risk terms
        for i in range(n):
            for j in range(n):
                Q[i, j] += lam * Sigma[i, j]

        # Budget penalty:  P*(sum x_i - K)^2 = P*sum_{ij} x_i x_j - 2PK sum_i x_i + PK^2
        for i in range(n):
            Q[i, i] += P * (1 - 2 * K)
            for j in range(n):
                if i != j:
                    Q[i, j] += P

        offset = P * K ** 2

        return QUBOProblem(
            Q=Q,
            offset=offset,
            symbols=self.dataset.symbols,
            meta={
                "type": "mean_variance_binary",
                "risk_aversion": lam,
                "budget": K,
                "penalty": P,
            },
        )
