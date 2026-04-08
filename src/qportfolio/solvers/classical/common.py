from __future__ import annotations

import math
import random
from typing import Dict, Iterable, List, Tuple

from qportfolio.solvers.base import PortfolioSolution


def _variables_from_payload(payload: dict) -> List[str]:
    if payload.get("type") == "qubo":
        return sorted(payload["qubo"].keys())
    if payload.get("type") == "ising":
        return sorted(payload["h"].keys())
    if payload.get("type") == "cqm":
        return sorted(payload["variables"].keys())
    return []


def _symbols_and_variable_map(payload: dict) -> tuple[list[str], dict[str, str]]:
    symbols = list(payload.get("symbols", []))
    variable_map = dict(payload.get("variable_map", {}))
    return symbols, variable_map


def _infer_target_from_metadata(payload: dict, key: str):
    metadata = payload.get("metadata", {})
    constraints = metadata.get("constraints") or metadata.get("raw_constraints") or {}
    return constraints.get(key)


def _evaluate_qubo(qubo: Dict[str, Dict[str, float]], assignment: Dict[str, int]) -> float:
    variables = sorted(qubo.keys())
    value = 0.0
    for left in variables:
        x_left = assignment.get(left, 0)
        value += qubo[left].get(left, 0.0) * x_left
    seen = set()
    for left in variables:
        for right in variables:
            if left == right:
                continue
            key = tuple(sorted((left, right)))
            if key in seen:
                continue
            seen.add(key)
            value += qubo[left].get(right, 0.0) * assignment.get(left, 0) * assignment.get(right, 0)
    return value


def _evaluate_cqm(payload: dict, assignment: Dict[str, int]) -> tuple[float, dict[str, float]]:
    objective = payload.get("objective", {})
    linear = objective.get("linear", {})
    quadratic = objective.get("quadratic", {})
    value = 0.0

    for var, coeff in linear.items():
        value += coeff * assignment.get(var, 0)

    seen = set()
    for left, row in quadratic.items():
        for right, coeff in row.items():
            key = tuple(sorted((left, right)))
            if key in seen:
                continue
            seen.add(key)
            value += coeff * assignment.get(left, 0) * assignment.get(right, 0)

    violations = {}
    for constraint in payload.get("constraints", []):
        lhs = sum(coeff * assignment.get(var, 0) for var, coeff in constraint.get("linear", {}).items())
        rhs = float(constraint.get("rhs", 0.0))
        sense = constraint.get("sense", "==")
        if sense == "==":
            violations[constraint["name"]] = abs(lhs - rhs)
        elif sense == "<=":
            violations[constraint["name"]] = max(0.0, lhs - rhs)
        elif sense == ">=":
            violations[constraint["name"]] = max(0.0, rhs - lhs)
        else:
            violations[constraint["name"]] = 0.0

    return value, violations


def evaluate_translated_problem(payload: dict, assignment: Dict[str, int]) -> tuple[float, dict[str, float]]:
    kind = payload.get("type")
    if kind == "qubo":
        value = _evaluate_qubo(payload["qubo"], assignment)
        violations = {}
        constraints = payload.get("metadata", {}).get("constraints", {})
        target_budget = constraints.get("budget")
        if target_budget is not None:
            violations["budget"] = abs(sum(assignment.values()) - int(target_budget))
        target_cardinality = constraints.get("cardinality")
        if target_cardinality is not None:
            violations["cardinality"] = abs(sum(assignment.values()) - int(target_cardinality))
        return value, violations

    if kind == "cqm":
        return _evaluate_cqm(payload, assignment)

    if kind == "ising":
        h = payload.get("h", {})
        J = payload.get("J", {})
        offset = float(payload.get("offset", 0.0))
        spins = {var: 1 - 2 * assignment.get(var, 0) for var in h.keys()}
        value = offset
        for var, coeff in h.items():
            value += coeff * spins[var]
        seen = set()
        for left, row in J.items():
            for right, coeff in row.items():
                key = tuple(sorted((left, right)))
                if key in seen:
                    continue
                seen.add(key)
                value += coeff * spins[left] * spins[right]
        violations = {}
        return value, violations

    raise ValueError(f"Unsupported translated problem type: {kind}")


def build_solution(payload: dict, assignment: Dict[str, int], objective_value: float, violations: Dict[str, float], solver_name: str, metadata: dict | None = None) -> PortfolioSolution:
    symbols, variable_map = _symbols_and_variable_map(payload)
    inverse = {var: sym for sym, var in variable_map.items()}

    selected_assets = [inverse[var] for var, bit in assignment.items() if bit == 1 and var in inverse]
    selected_assets = sorted(selected_assets)

    selected_count = len(selected_assets)
    if selected_count == 0:
        weights = {symbol: 0.0 for symbol in symbols}
    else:
        equal_weight = 1.0 / selected_count
        weights = {symbol: (equal_weight if symbol in selected_assets else 0.0) for symbol in symbols}

    feasible = all(value == 0.0 for value in violations.values()) if violations else True

    return PortfolioSolution(
        selected_assets=selected_assets,
        assignment=dict(sorted(assignment.items())),
        weights=weights,
        objective_value=objective_value,
        feasible=feasible,
        constraint_violations=violations,
        metadata={"solver": solver_name, **(metadata or {})},
    )


def all_binary_assignments(variables: List[str]) -> Iterable[Dict[str, int]]:
    total = len(variables)
    for mask in range(1 << total):
        yield {variables[i]: ((mask >> i) & 1) for i in range(total)}


def random_assignment(variables: List[str], rng: random.Random) -> Dict[str, int]:
    return {var: rng.randint(0, 1) for var in variables}


def single_flip_neighbors(assignment: Dict[str, int]) -> Iterable[Dict[str, int]]:
    variables = list(assignment.keys())
    for var in variables:
        candidate = dict(assignment)
        candidate[var] = 1 - candidate[var]
        yield candidate
