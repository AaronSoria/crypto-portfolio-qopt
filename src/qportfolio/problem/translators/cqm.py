from __future__ import annotations

from typing import Dict, Any

from qportfolio.problem.encodings.binary import binary_encoding_map
from base import ProblemTranslator


class CQMTranslator(ProblemTranslator):
    target_type = "cqm"

    def translate(self, problem) -> Dict[str, Any]:
        qf = problem.to_quadratic_form()
        variable_map = binary_encoding_map(qf["symbols"])

        objective = {
            "sense": "minimize",
            "linear": {
                variable_map[symbol]: qf["linear"].get(symbol, 0.0)
                for symbol in qf["symbols"]
            },
            "quadratic": {
                variable_map[left]: {
                    variable_map[right]: qf["quadratic"].get(left, {}).get(right, 0.0)
                    for right in qf["symbols"]
                    if left != right
                }
                for left in qf["symbols"]
            },
        }

        constraints = []
        if qf["constraints"].get("budget") is not None:
            constraints.append({
                "name": "budget",
                "sense": "==",
                "rhs": int(qf["constraints"]["budget"]),
                "linear": {variable_map[symbol]: 1.0 for symbol in qf["symbols"]},
            })

        if qf["constraints"].get("cardinality") is not None:
            constraints.append({
                "name": "cardinality",
                "sense": "==",
                "rhs": int(qf["constraints"]["cardinality"]),
                "linear": {variable_map[symbol]: 1.0 for symbol in qf["symbols"]},
            })

        return {
            "type": self.target_type,
            "problem_name": qf["name"],
            "symbols": qf["symbols"],
            "variable_map": variable_map,
            "variables": {
                variable_map[symbol]: {"type": "binary"} for symbol in qf["symbols"]
            },
            "objective": objective,
            "constraints": constraints,
            "metadata": {
                "risk_aversion": qf["risk_aversion"],
                "raw_constraints": qf["constraints"],
            },
        }
