from pathlib import Path
import argparse
import yaml

from qportfolio.benchmark.runner import BenchmarkRunner


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    config = yaml.safe_load(config_path.read_text())
    runner = BenchmarkRunner()
    result = runner.run_from_config(config)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
