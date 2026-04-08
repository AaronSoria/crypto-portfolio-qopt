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
    problem = _ensure_dict(config.get("problem"), "problem")
    translator = _ensure_dict(config.get("translator"), "translator")
    solver = _ensure_dict(config.get("solver"), "solver")
    provider = _ensure_dict(config.get("provider"), "provider")
    data = _ensure_dict(config.get("data"), "data")

    return {
        "experiment_name": config.get("experiment_name", "example_mean_variance"),
        "data": {
            "source": data.get("source", "in_memory"),
            "snapshot_name": data.get("snapshot_name", "default"),
        },
        "problem": {
            "type": problem.get("type", "mean_variance_binary"),
            "risk_aversion": float(problem.get("risk_aversion", 1.0)),
            "expected_returns": problem.get("expected_returns", {}),
            "covariance_matrix": problem.get("covariance_matrix", {}),
            "constraints": problem.get("constraints", {}),
        },
        "translator": {
            "type": translator.get("type", "qubo"),
        },
        "solver": {
            "type": solver.get("type", "greedy"),
            "parameters": solver.get("parameters", {}),
        },
        "provider": {
            "type": provider.get("type", "local_simulator"),
            "parameters": provider.get("parameters", {}),
        },
    }


def load_and_normalize_config(path: str) -> Dict[str, Any]:
    return normalize_experiment_config(load_yaml_config(path))
