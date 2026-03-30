from qportfolio.benchmark.runner import BenchmarkRunner


def test_smoke_runner() -> None:
    result = BenchmarkRunner().run_from_config({"name": "smoke", "problem": {}})
    assert result.solver_name == "greedy"
    assert result.translated_problem_type == "qubo"
