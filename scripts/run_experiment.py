from __future__ import annotations

import argparse
import json

from qportfolio.benchmark.runner import BenchmarkRunner
from qportfolio.config.loader import load_and_normalize_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a benchmark experiment from YAML config.")
    parser.add_argument("--config", required=True, help="Path to experiment YAML config.")
    parser.add_argument("--persist", action="store_true", help="Persist the benchmark output as JSON.")
    parser.add_argument("--output-dir", default="results/logs", help="Directory where benchmark JSON logs are written.")
    args = parser.parse_args()

    config = load_and_normalize_config(args.config)
    runner = BenchmarkRunner()
    result = runner.run_from_config(config, persist=args.persist, output_dir=args.output_dir)
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
