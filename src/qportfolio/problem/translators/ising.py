from __future__ import annotations

from typing import Dict, Any

from qubo import QuboTranslator
from base import ProblemTranslator


class IsingTranslator(ProblemTranslator):
    target_type = "ising"

    def translate(self, problem) -> Dict[str, Any]:
        qubo_payload = QuboTranslator().translate(problem)
        qubo = qubo_payload["qubo"]
        variables = list(qubo.keys())

        h: Dict[str, float] = {var: 0.0 for var in variables}
        j: Dict[str, Dict[str, float]] = {
            left: {right: 0.0 for right in variables} for left in variables
        }
        offset = 0.0

        # x = (1 - s) / 2
        # Q_ii x_i contributes:
        #   +Q_ii/2 to offset, -Q_ii/2 to h_i
        # Q_ij x_i x_j contributes:
        #   +Q_ij/4 to offset, -Q_ij/4 to h_i, -Q_ij/4 to h_j, +Q_ij/4 to J_ij
        for left in variables:
            diag = qubo[left].get(left, 0.0)
            offset += diag / 2.0
            h[left] -= diag / 2.0

        seen = set()
        for left in variables:
            for right in variables:
                if left == right:
                    continue
                key = tuple(sorted((left, right)))
                if key in seen:
                    continue
                seen.add(key)

                q = qubo[left].get(right, 0.0)
                if q == 0.0:
                    continue

                offset += q / 4.0
                h[left] -= q / 4.0
                h[right] -= q / 4.0
                j[left][right] += q / 4.0
                j[right][left] += q / 4.0

        return {
            "type": self.target_type,
            "problem_name": qubo_payload["problem_name"],
            "symbols": qubo_payload["symbols"],
            "variable_map": qubo_payload["variable_map"],
            "h": h,
            "J": j,
            "offset": offset,
            "metadata": qubo_payload["metadata"],
        }
