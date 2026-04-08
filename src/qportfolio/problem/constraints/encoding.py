from __future__ import annotations

from typing import Dict, Any


def apply_binary_constraints(
    symbols: list[str],
    linear: Dict[str, float],
    quadratic: Dict[str, Dict[str, float]],
    constraints: Dict[str, Any],
) -> dict:
    """
    Encode binary portfolio constraints as quadratic penalties.

    Supported:
    - budget: sum(x_i) = budget
    - cardinality: sum(x_i) = k

    Penalty form:
        P * (sum x_i - target)^2
    for x_i in {0,1}.
    """
    out_linear = {k: float(v) for k, v in linear.items()}
    out_quadratic = {
        left: {right: float(value) for right, value in row.items()}
        for left, row in quadratic.items()
    }

    penalty = float(constraints.get("penalty", 10.0) or 10.0)

    for key in ("budget", "cardinality"):
        target = constraints.get(key)
        if target is None:
            continue

        target = int(target)
        for symbol in symbols:
            # P * (1 - 2 target) x_i because x_i^2 = x_i
            out_linear[symbol] = out_linear.get(symbol, 0.0) + penalty * (1 - 2 * target)

        for i, left in enumerate(symbols):
            for right in symbols[i + 1:]:
                coeff = 2.0 * penalty
                out_quadratic.setdefault(left, {})
                out_quadratic.setdefault(right, {})
                out_quadratic[left][right] = out_quadratic[left].get(right, 0.0) + coeff
                out_quadratic[right][left] = out_quadratic[right].get(left, 0.0) + coeff

    return {
        "symbols": symbols,
        "linear": out_linear,
        "quadratic": out_quadratic,
        "constraints": constraints,
    }
