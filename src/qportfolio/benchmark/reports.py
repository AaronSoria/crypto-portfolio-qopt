from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


def persist_result(result: Dict[str, Any], output_dir: str = "results/logs") -> str:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    experiment_name = result.get("experiment_name", "benchmark_run")
    safe_name = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in experiment_name)
    filename = f"{timestamp}_{safe_name}.json"

    destination = output_path / filename
    destination.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return str(destination)


def load_results(log_dir: str = "results/logs") -> list[Dict[str, Any]]:
    path = Path(log_dir)
    if not path.exists():
        return []

    items: list[Dict[str, Any]] = []
    for file_path in sorted(path.glob("*.json")):
        items.append(json.loads(file_path.read_text(encoding="utf-8")))
    return items


def generate_summary_report(results: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(results)
    if not rows:
        return {
            "runs": 0,
            "best_objective_value": None,
            "best_experiment_name": None,
            "feasible_runs": 0,
            "average_runtime_seconds": 0.0,
        }

    best = min(rows, key=lambda item: item.get("metrics", {}).get("objective_value", float("inf")))
    feasible_runs = sum(1 for item in rows if item.get("metrics", {}).get("feasible", False))
    avg_runtime = sum(item.get("metrics", {}).get("total_runtime_seconds", 0.0) for item in rows) / len(rows)

    return {
        "runs": len(rows),
        "best_objective_value": best.get("metrics", {}).get("objective_value"),
        "best_experiment_name": best.get("experiment_name"),
        "feasible_runs": feasible_runs,
        "average_runtime_seconds": avg_runtime,
    }


def format_report_text(summary: Dict[str, Any], results: Iterable[Dict[str, Any]]) -> str:
    rows = list(results)
    lines = [
        "Benchmark Report",
        "================",
        f"Runs: {summary.get('runs', 0)}",
        f"Feasible runs: {summary.get('feasible_runs', 0)}",
        f"Best objective value: {summary.get('best_objective_value')}",
        f"Best experiment: {summary.get('best_experiment_name')}",
        f"Average runtime (s): {summary.get('average_runtime_seconds', 0.0):.6f}",
        "",
        "Runs detail:",
    ]

    for item in rows:
        metrics = item.get("metrics", {})
        lines.append(
            f"- {item.get('experiment_name')} | solver={item.get('solver_name')} | "
            f"translator={item.get('translator_type')} | objective={metrics.get('objective_value')} | "
            f"feasible={metrics.get('feasible')} | runtime={metrics.get('total_runtime_seconds', 0.0):.6f}s"
        )

    return "\n".join(lines)
