"""
Benchmark runner — compares classical and Pasqal quantum solvers
on the same QUBO instance and produces a unified report.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from .data import PortfolioDataset
from .problem import MeanVarianceBinaryProblem, QUBOProblem
from .solver_classical import ClassicalSolverResult, ExactSolver, GreedySolver
from .solver_pasqal import PasqalNeutralAtomSolver, PasqalSolverResult


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
    """
    Full benchmark pipeline from config dict.

    Config schema (matches configs/experiments/example_mean_variance.yaml):
      data.source: "in_memory" | "json"
      problem.type: "mean_variance_binary"
      solver.type: "pasqal" | "greedy" | "exact"
      ...
    """
    # ── 1. Load data ────────────────────────────────────────────────────────
    data_cfg = config.get("data", {})
    prob_cfg = config.get("problem", {})
    solver_cfg = config.get("solver", {})
    pasqal_cfg = config.get("pasqal", {})

    source = data_cfg.get("source", "in_memory")
    if source == "in_memory":
        dataset = PortfolioDataset.from_config(prob_cfg)
    elif source == "json":
        path = data_cfg.get("path", "data/portfolio.json")
        dataset = PortfolioDataset.from_json(path)
    else:
        raise ValueError(f"Unknown data source: {source}")

    # ── 2. Build QUBO ────────────────────────────────────────────────────────
    prob = MeanVarianceBinaryProblem(
        dataset=dataset,
        risk_aversion=prob_cfg.get("risk_aversion", 0.5),
        budget=prob_cfg.get("constraints", {}).get("budget", 2),
        penalty=prob_cfg.get("constraints", {}).get("penalty", 10.0),
    )
    qubo = prob.build_qubo()

    # ── 3. Exact (if feasible) ───────────────────────────────────────────────
    exact_result = None
    if qubo.n <= 15:
        exact = ExactSolver()
        exact_result = exact.solve(qubo)

    # ── 4. Classical greedy ──────────────────────────────────────────────────
    greedy = GreedySolver(
        max_iterations=solver_cfg.get("parameters", {}).get("max_iterations", 500),
        seed=config.get("seed", 42),
    )
    t0 = time.perf_counter()
    greedy_res = greedy.solve(qubo)
    greedy_time = time.perf_counter() - t0

    # ── 5. Pasqal solver ─────────────────────────────────────────────────────
    pasqal_solver = PasqalNeutralAtomSolver(
        n_shots=pasqal_cfg.get("n_shots", 1000),
        omega_max=pasqal_cfg.get("omega_max", 2 * 3.14159 * 4),
        delta_start=pasqal_cfg.get("delta_start", -2 * 3.14159 * 5),
        delta_end=pasqal_cfg.get("delta_end", 2 * 3.14159 * 5),
        lattice_spacing_um=pasqal_cfg.get("lattice_spacing_um", 6.0),
        blockade_radius_um=pasqal_cfg.get("blockade_radius_um", 7.0),
        n_time_steps=pasqal_cfg.get("n_time_steps", 80),
        seed=config.get("seed", 42),
        use_pulser=pasqal_cfg.get("use_pulser", True),
        pasqal_cloud_token=pasqal_cfg.get("cloud_token", ""),
    )
    t0 = time.perf_counter()
    pasqal_res = pasqal_solver.solve(qubo)
    pasqal_time = time.perf_counter() - t0

    # ── 6. Assemble report ───────────────────────────────────────────────────
    opt_energy = exact_result.best_energy if exact_result else None
    opt_sel = exact_result.best_selection if exact_result else None

    pasqal_gap = None
    greedy_gap = None
    if opt_energy is not None:
        pasqal_gap = pasqal_res.best_energy - opt_energy
        greedy_gap = greedy_res.best_energy - opt_energy

    return BenchmarkResult(
        experiment_name=experiment_name,
        symbols=dataset.symbols,
        qubo_size=qubo.n,
        qubo_matrix=qubo.Q.tolist(),
        optimal_energy=opt_energy,
        optimal_selection=opt_sel,
        greedy={
            "selection": greedy_res.best_selection,
            "energy": greedy_res.best_energy,
            "bitstring": greedy_res.best_bitstring,
            "time_s": greedy_time,
        },
        pasqal={
            "selection": pasqal_res.best_selection,
            "energy": pasqal_res.best_energy,
            "bitstring": pasqal_res.best_bitstring,
            "backend": pasqal_res.backend,
            "n_shots": pasqal_res.n_shots,
            "time_s": pasqal_time,
            "top5": pasqal_res.top_k(5),
            "register_positions_um": pasqal_res.register_positions.tolist(),
        },
        pasqal_vs_optimal_gap=pasqal_gap,
        greedy_vs_optimal_gap=greedy_gap,
    )


def print_report(result: BenchmarkResult) -> None:
    sep = "─" * 60
    print(f"\n{'═'*60}")
    print(f"  Experiment: {result.experiment_name}")
    print(f"  Assets: {result.symbols}  (QUBO size: {result.qubo_size})")
    print(f"{'═'*60}")

    if result.optimal_energy is not None:
        print(f"  ✓ Exact optimal  → {result.optimal_selection}  E={result.optimal_energy:.4f}")
    else:
        print("  ⚠ Exact solution not computed (n > 15)")

    print(sep)
    g = result.greedy
    print(f"  Classical greedy → {g['selection']}  E={g['energy']:.4f}  [{g['time_s']*1000:.1f} ms]")
    if result.greedy_vs_optimal_gap is not None:
        print(f"    Gap vs optimal: {result.greedy_vs_optimal_gap:+.4f}")

    print(sep)
    p = result.pasqal
    print(f"  🔬 Pasqal ({p['backend']}) → {p['selection']}  E={p['energy']:.4f}  [{p['time_s']*1000:.1f} ms]")
    print(f"     Backend: {p['backend']}  |  Shots: {p['n_shots']}")
    if result.pasqal_vs_optimal_gap is not None:
        print(f"     Gap vs optimal: {result.pasqal_vs_optimal_gap:+.4f}")

    print(f"     Top-5 sampled states:")
    for bits, energy, count in p.get("top5", []):
        symbols = [result.symbols[i] for i, b in enumerate(bits) if b == "1"]
        print(f"       {bits}  sel={symbols}  E={energy:.4f}  count={count}")

    print(f"{'═'*60}\n")
