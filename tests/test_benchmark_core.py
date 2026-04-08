from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qportfolio.benchmark import (
    BenchmarkRunner,
    load_results,
    generate_summary_report,
    format_report_text,
)
from qportfolio.config import normalize_experiment_config


def _raw_config():
    return {
        "experiment_name": "unit_test_benchmark",
        "problem": {
            "type": "mean_variance_binary",
            "risk_aversion": 0.5,
            "expected_returns": {"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
            "covariance_matrix": {
                "BTC": {"BTC": 0.30, "ETH": 0.10, "SOL": 0.05},
                "ETH": {"BTC": 0.10, "ETH": 0.25, "SOL": 0.07},
                "SOL": {"BTC": 0.05, "ETH": 0.07, "SOL": 0.20},
            },
            "constraints": {"budget": 2, "penalty": 12.0},
        },
        "translator": {"type": "qubo"},
        "solver": {"type": "greedy", "parameters": {}},
        "provider": {"type": "local_simulator", "parameters": {"execution_cost": 0.0}},
    }


def test_normalize_experiment_config_applies_defaults():
    cfg = normalize_experiment_config(_raw_config())
    assert cfg["experiment_name"] == "unit_test_benchmark"
    assert cfg["translator"]["type"] == "qubo"
    assert cfg["solver"]["type"] == "greedy"
    assert cfg["provider"]["type"] == "local_simulator"


def test_benchmark_runner_executes_and_persists(tmp_path):
    cfg = normalize_experiment_config(_raw_config())
    runner = BenchmarkRunner()

    result = runner.run_from_config(cfg, persist=True, output_dir=str(tmp_path))

    assert result.experiment_name == "unit_test_benchmark"
    assert result.translator_type == "qubo"
    assert result.solver_name == "greedy"
    assert result.provider_name == "local_simulator"
    assert result.metrics["selected_asset_count"] == 2
    assert result.persisted_path is not None

    loaded = load_results(str(tmp_path))
    assert len(loaded) == 1
    assert loaded[0]["experiment_name"] == "unit_test_benchmark"


def test_generate_summary_report_and_format_text(tmp_path):
    cfg = normalize_experiment_config(_raw_config())
    runner = BenchmarkRunner()
    runner.run_from_config(cfg, persist=True, output_dir=str(tmp_path))

    results = load_results(str(tmp_path))
    summary = generate_summary_report(results)
    text = format_report_text(summary, results)

    assert summary["runs"] == 1
    assert summary["feasible_runs"] == 1
    assert "Benchmark Report" in text
    assert "unit_test_benchmark" in text
