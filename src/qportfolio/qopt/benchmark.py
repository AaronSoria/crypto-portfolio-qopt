"""
Benchmark pipeline — compares classical and Pasqal quantum solvers for n assets.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .data import PortfolioDataset
from .problem import MeanVarianceBinaryProblem, QUBOProblem
from .solver_classical import ClassicalSolverResult, ExactSolver, GreedySolver
from .solver_pasqal import PasqalNeutralAtomSolver, PasqalSolverResult


EXACT_SOLVER_MAX_N = 15   # brute-force feasible limit


@dataclass
class BenchmarkResult:
    experiment_name: str
    symbols: List[str]
    qubo_size: int
    qubo_matrix: List[List[float]]
    optimal_energy: Optional[float]
    optimal_selection: Optional[List[str]]
    greedy: Dict[str, Any]
    pasqal: Dict[str, Any]
    pasqal_vs_optimal_gap: Optional[float]
    greedy_vs_optimal_gap: Optional[float]


def run_benchmark(config: dict, experiment_name: str = "unnamed") -> BenchmarkResult:
    data_cfg   = config.get("data", {})
    prob_cfg   = config.get("problem", {})
    solver_cfg = config.get("solver", {})
    pasqal_cfg = config.get("pasqal", {})

    # 1. Load dataset
    source = data_cfg.get("source", "in_memory")
    if source == "in_memory":
        dataset = PortfolioDataset.from_config(prob_cfg)
    elif source == "json":
        dataset = PortfolioDataset.from_json(data_cfg.get("path", "data/raw/market_snapshot.json"))
    else:
        raise ValueError(f"Unknown data source: {source}")

    # 2. Derive budget from config or default to n//3 (sensible for any n)
    n = dataset.n
    default_budget = max(1, n // 3)
    constraints = prob_cfg.get("constraints", {})
    budget  = constraints.get("budget", default_budget)
    penalty = constraints.get("penalty", float(budget) * 10.0)

    print(f"  [benchmark] n={n} assets  budget={budget}  penalty={penalty:.1f}")

    # 3. Build QUBO
    prob = MeanVarianceBinaryProblem(
        dataset=dataset,
        risk_aversion=prob_cfg.get("risk_aversion", 0.5),
        budget=budget,
        penalty=penalty,
    )
    qubo = prob.build_qubo()

    # 4. Exact solver (only for small n)
    exact_result = None
    if qubo.n <= EXACT_SOLVER_MAX_N:
        exact_result = ExactSolver().solve(qubo)

    # 5. Classical greedy
    t0 = time.perf_counter()
    greedy_res = GreedySolver(
        max_iterations=solver_cfg.get("parameters", {}).get("max_iterations", 500),
        seed=config.get("seed", 42),
    ).solve(qubo)
    greedy_time = time.perf_counter() - t0

    # 6. Pasqal solver
    pasqal_solver = PasqalNeutralAtomSolver(
        n_shots             = pasqal_cfg.get("n_shots", 1000),
        backend             = pasqal_cfg.get("backend", "auto"),
        omega_max           = pasqal_cfg.get("omega_max", 2 * 3.14159265 * 4),
        delta_start         = pasqal_cfg.get("delta_start", 2 * 3.14159265 * -5),
        delta_end           = pasqal_cfg.get("delta_end",   2 * 3.14159265 *  5),
        lattice_spacing_um  = pasqal_cfg.get("lattice_spacing_um", 10.5),
        blockade_radius_um  = pasqal_cfg.get("blockade_radius_um", 7.0),
        n_time_steps        = pasqal_cfg.get("n_time_steps", 100),
        sa_maxiter          = pasqal_cfg.get("sa_maxiter", 10_000),
        seed                = config.get("seed", 42),
        use_pulser          = pasqal_cfg.get("use_pulser", True),
        cloud_token         = pasqal_cfg.get("cloud_token", ""),
        project_id          = pasqal_cfg.get("project_id", ""),
    )
    pasqal_res = pasqal_solver.solve(qubo)

    # 7. Gaps
    opt_energy = exact_result.best_energy if exact_result else None
    opt_sel    = exact_result.best_selection if exact_result else None
    pasqal_gap = (pasqal_res.best_energy - opt_energy) if opt_energy is not None else None
    greedy_gap = (greedy_res.best_energy  - opt_energy) if opt_energy is not None else None

    return BenchmarkResult(
        experiment_name      = experiment_name,
        symbols              = dataset.symbols,
        qubo_size            = qubo.n,
        qubo_matrix          = qubo.Q.tolist(),
        optimal_energy       = opt_energy,
        optimal_selection    = opt_sel,
        greedy               = {
            "selection": greedy_res.best_selection,
            "energy":    greedy_res.best_energy,
            "bitstring": greedy_res.best_bitstring,
            "time_s":    greedy_time,
        },
        pasqal               = pasqal_res.to_dict(),
        pasqal_vs_optimal_gap = pasqal_gap,
        greedy_vs_optimal_gap = greedy_gap,
    )


def print_report(result: BenchmarkResult) -> None:
    SEP  = "─" * 62
    WIDE = "═" * 62

    print(f"\n{WIDE}")
    print(f"  Experiment : {result.experiment_name}")
    print(f"  Assets     : {result.symbols}")
    print(f"  QUBO size  : {result.qubo_size} x {result.qubo_size}  ({result.qubo_size} qubits)")
    print(WIDE)

    if result.optimal_energy is not None:
        print(f"  Exact optimal  ->  {result.optimal_selection}  E={result.optimal_energy:.6f}")
    else:
        print(f"  Exact solver   ->  skipped (n > {EXACT_SOLVER_MAX_N})")

    print(SEP)
    g = result.greedy
    print(f"  Classical greedy  ->  {g['selection']}  E={g['energy']:.6f}  [{g['time_s']*1000:.1f} ms]")
    if result.greedy_vs_optimal_gap is not None:
        print(f"    gap vs optimal: {result.greedy_vs_optimal_gap:+.6f}")

    print(SEP)
    p = result.pasqal
    print(f"  Pasqal ({p['backend']})  ->  {p['best_selection']}  E={p['best_energy']:.6f}  [{p['solve_time_s']*1000:.1f} ms]")
    print(f"    backend: {p['backend']}  |  n_assets: {p['n_assets']}  |  shots: {p['n_shots']}")
    if result.pasqal_vs_optimal_gap is not None:
        print(f"    gap vs optimal: {result.pasqal_vs_optimal_gap:+.6f}")

    print(f"    top-5 states:")
    for bs, energy, count in p.get("top5", []):
        sel = [result.symbols[i] for i, b in enumerate(bs) if b == "1"]
        print(f"      |{bs}>  {str(sel):30s}  E={energy:.6f}  shots={count}")

    print(WIDE + "\n")
