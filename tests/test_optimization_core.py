from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from qportfolio.problem.models import MeanVarianceBinaryProblem, ConstraintSet
from qportfolio.problem.encodings import binary_encoding_map, inverse_binary_encoding_map
from qportfolio.problem.translators import QuboTranslator, IsingTranslator, CQMTranslator


def _build_problem():
    return MeanVarianceBinaryProblem(
        expected_returns={"BTC": 0.12, "ETH": 0.08, "SOL": 0.10},
        covariance_matrix={
            "BTC": {"BTC": 0.30, "ETH": 0.10, "SOL": 0.05},
            "ETH": {"BTC": 0.10, "ETH": 0.25, "SOL": 0.07},
            "SOL": {"BTC": 0.05, "ETH": 0.07, "SOL": 0.20},
        },
        risk_aversion=0.5,
        constraints=ConstraintSet(budget=2, penalty=12.0),
    )


def test_binary_encoding_map_roundtrip():
    mapping = binary_encoding_map(["BTC", "ETH"])
    inverse = inverse_binary_encoding_map(["BTC", "ETH"])

    assert mapping["BTC"] == "x_BTC"
    assert mapping["ETH"] == "x_ETH"
    assert inverse["x_BTC"] == "BTC"
    assert inverse["x_ETH"] == "ETH"


def test_mean_variance_formulation_contains_linear_and_quadratic_terms():
    problem = _build_problem()
    qf = problem.to_quadratic_form()

    assert qf["linear"]["BTC"] == -0.12
    assert qf["quadratic"]["BTC"]["BTC"] == 0.15
    assert qf["quadratic"]["ETH"]["SOL"] == 0.035
    assert qf["constraints"]["budget"] == 2


def test_qubo_translator_builds_variable_mapped_qubo():
    payload = QuboTranslator().translate(_build_problem())

    assert payload["type"] == "qubo"
    assert payload["variable_map"]["BTC"] == "x_BTC"
    assert "x_BTC" in payload["qubo"]
    assert "x_ETH" in payload["qubo"]["x_BTC"]
    assert payload["metadata"]["constraints"]["budget"] == 2


def test_ising_translator_produces_h_j_and_offset():
    payload = IsingTranslator().translate(_build_problem())

    assert payload["type"] == "ising"
    assert "x_BTC" in payload["h"]
    assert "x_ETH" in payload["J"]["x_BTC"]
    assert isinstance(payload["offset"], float)


def test_cqm_translator_builds_binary_variables_and_constraints():
    payload = CQMTranslator().translate(_build_problem())

    assert payload["type"] == "cqm"
    assert payload["variables"]["x_BTC"]["type"] == "binary"
    assert payload["objective"]["sense"] == "minimize"
    assert any(constraint["name"] == "budget" for constraint in payload["constraints"])
