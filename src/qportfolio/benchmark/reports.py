from pathlib import Path
from datetime import datetime

from qportfolio.benchmark.runner import BenchmarkRunResult


def persist_result(result: BenchmarkRunResult, output_dir: str = "results/logs") -> Path:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{result.experiment_name}.json"
    path.write_text(result.model_dump_json(indent=2))
    return path
