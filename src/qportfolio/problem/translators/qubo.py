from __future__ import annotations

from typing import Any, Dict

from qportfolio.problem.constraints.encoding import apply_binary_constraints
from qportfolio.problem.encodings.binary import binary_encoding_map
from .base import ProblemTranslator


class QuboTranslator(ProblemTranslator):
    target_type = "qubo"

    def translate(self, problem) -> Dict[str, Any]:
        qf = problem.to_quadratic_form()
        constrained = apply_binary_constraints(
            qf["symbols"],
            qf["linear"],
            qf["quadratic"],
            qf["constraints"],
        )
        variable_map = binary_encoding_map(qf["symbols"])

        qubo: Dict[str, Dict[str, float]] = {
            variable_map[left]: {variable_map[right]: 0.0 for right in qf["symbols"]}
            for left in qf["symbols"]
        }

        for symbol in qf["symbols"]:
            variable = variable_map[symbol]
            qubo[variable][variable] = constrained["linear"].get(symbol, 0.0)

        for left in qf["symbols"]:
            left_var = variable_map[left]
            for right in qf["symbols"]:
                if left == right:
                    continue
                right_var = variable_map[right]
                qubo[left_var][right_var] = constrained["quadratic"].get(left, {}).get(right, 0.0)

        return {
            "type": self.target_type,
            "problem_name": qf["name"],
            "symbols": qf["symbols"],
            "variable_map": variable_map,
            "qubo": qubo,
            "metadata": {
                "risk_aversion": qf["risk_aversion"],
                "constraints": qf["constraints"],
            },
        }
