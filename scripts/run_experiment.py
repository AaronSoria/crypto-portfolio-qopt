#!/usr/bin/env python3
"""
run_experiment.py — entry point for portfolio optimisation experiments.

Usage:
    python run_experiment.py --config configs/experiments/example_mean_variance.yaml
    python run_experiment.py --config configs/experiments/example_mean_variance.yaml --solver pasqal
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent.parent))

from qopt.benchmark import print_report, run_benchmark


def main():
    parser = argparse.ArgumentParser(description="Crypto Portfolio QOpt Experiment Runner")
    parser.add_argument(
        "--config",
        default="configs/experiments/example_mean_variance.yaml",
        help="Path to experiment YAML config",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON results",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"[ERROR] Config not found: {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    experiment_name = config.get("experiment_name", config_path.stem)
    print(f"\n[*] Loading experiment: {experiment_name}")
    print(f"[*] Config: {config_path}")

    result = run_benchmark(config, experiment_name=experiment_name)
    print_report(result)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            # Convert numpy arrays for JSON serialisation
            data = {
                "experiment": result.experiment_name,
                "symbols": result.symbols,
                "qubo_size": result.qubo_size,
                "optimal_energy": result.optimal_energy,
                "optimal_selection": result.optimal_selection,
                "greedy": result.greedy,
                "pasqal": {k: v for k, v in result.pasqal.items() if k != "register_positions_um"},
                "pasqal_gap": result.pasqal_vs_optimal_gap,
                "greedy_gap": result.greedy_vs_optimal_gap,
            }
            json.dump(data, f, indent=2, default=str)
        print(f"[*] Results saved to {out}")


if __name__ == "__main__":
    main()
