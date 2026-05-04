#!/usr/bin/env python3
"""
run_experiment.py — entry point for portfolio optimisation experiments.

Usage (matches docker-compose CMD):
    python scripts/run_experiment.py \
        --config configs/experiments/pasqal_mean_variance.yaml \
        --persist \
        --output-dir results/logs

Local dev:
    python scripts/run_experiment.py --config configs/experiments/pasqal_mean_variance.yaml
"""
import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from qopt.benchmark import print_report, run_benchmark


def main():
    parser = argparse.ArgumentParser(description="Crypto Portfolio QOpt — experiment runner")
    parser.add_argument(
        "--config",
        default="configs/experiments/example_mean_variance.yaml",
        help="Path to experiment YAML config",
    )
    parser.add_argument(
        "--persist",
        action="store_true",
        help="Write JSON results to --output-dir",
    )
    parser.add_argument(
        "--output-dir",
        default="results/logs",
        help="Directory for JSON result files (used with --persist)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    experiment_name = config.get("experiment_name", config_path.stem)
    print(f"\n[*] Experiment : {experiment_name}")
    print(f"[*] Config     : {config_path}")

    result = run_benchmark(config, experiment_name=experiment_name)
    print_report(result)

    if args.persist:
        out_dir = Path(args.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{experiment_name}.json"

        data = {
            "experiment": result.experiment_name,
            "symbols": result.symbols,
            "qubo_size": result.qubo_size,
            "optimal_energy": result.optimal_energy,
            "optimal_selection": result.optimal_selection,
            "greedy": result.greedy,
            "pasqal": {k: v for k, v in result.pasqal.items()
                       if k not in ("register_positions_um", "top5")},
            "pasqal_gap": result.pasqal_vs_optimal_gap,
            "greedy_gap": result.greedy_vs_optimal_gap,
        }
        with open(out_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        print(f"[*] Results saved → {out_path}")


if __name__ == "__main__":
    main()
