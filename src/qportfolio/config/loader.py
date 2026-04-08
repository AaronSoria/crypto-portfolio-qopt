from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml_config(path: str) -> Dict[str, Any]:
    file_path = Path(path)
    data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("The configuration file must contain a YAML mapping at the root.")
    return data


def _ensure_dict(value: Any, name: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"'{name}' must be a mapping.")
    return value


def normalize_experiment_config(config: Dict[str, Any]) -> Dict[str, Any]:
    problem_raw = _ensure_dict(config.get("problem"), "problem")

    translator_raw = config.get("translator")
    if isinstance(translator_raw, str):
        translator = {"type": translator_raw}
    else:
        translator = _ensure_dict(translator_raw, "translator")

    solver_raw = config.get("solver")
    solver = _ensure_dict(solver_raw, "solver")

    provider_raw = config.get("provider")
    provider = _ensure_dict(provider_raw, "provider")

    data = _ensure_dict(config.get("data"), "data")

    constraints = _ensure_dict(problem_raw.get("constraints"), "problem.constraints")

    # Backward-compatible lifting from the older experiment schema.
    for lifted_key in ("budget", "cardinality", "min_weight", "max_weight", "turnover", "long_only", "penalty"):
        if lifted_key in problem_raw and lifted_key not in constraints:
            constraints[lifted_key] = problem_raw.get(lifted_key)

    experiment_name = config.get("experiment_name") or config.get("name") or "example_mean_variance"
    problem_type = problem_raw.get("type") or problem_raw.get("model") or "mean_variance_binary"
    translator_type = translator.get("type") or "qubo"
    solver_type = solver.get("type") or solver.get("name") or "greedy"
    provider_type = provider.get("type") or provider.get("name") or "local_simulator"

    return {
        "experiment_name": experiment_name,
        "data": {
            "source": data.get("source", "in_memory"),
            "snapshot_name": data.get("snapshot_name") or config.get("data_snapshot") or "default",
        },
        "problem": {
            "type": problem_type,
            "risk_aversion": float(problem_raw.get("risk_aversion", 1.0)),
            "expected_returns": problem_raw.get(
                "expected_returns",
                {
                    "BTC": 0.12,
                    "ETH": 0.08,
                    "SOL": 0.10,
                },
            ),
            "covariance_matrix": problem_raw.get(
                "covariance_matrix",
                {
                    "BTC": {"BTC": 0.30, "ETH": 0.10, "SOL": 0.05},
                    "ETH": {"BTC": 0.10, "ETH": 0.25, "SOL": 0.07},
                    "SOL": {"BTC": 0.05, "ETH": 0.07, "SOL": 0.20},
                },
            ),
            "constraints": {
                "budget": constraints.get("budget"),
                "cardinality": constraints.get("cardinality"),
                "min_weight": constraints.get("min_weight"),
                "max_weight": constraints.get("max_weight"),
                "turnover": constraints.get("turnover"),
                "long_only": constraints.get("long_only", True),
                "penalty": float(constraints.get("penalty", 10.0)),
                "extras": constraints.get("extras", {}),
            },
        },
        "translator": {
            "type": str(translator_type).lower(),
        },
        "solver": {
            "type": str(solver_type).lower(),
            "parameters": solver.get("parameters", {}),
            "family": solver.get("family", "classical"),
        },
        "provider": {
            "type": str(provider_type).lower(),
            "parameters": provider.get("parameters", {}),
        },
    }


def load_and_normalize_config(path: str) -> Dict[str, Any]:
    return normalize_experiment_config(load_yaml_config(path))
