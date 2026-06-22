"""
Pasqal QUBO Solver — integración con qubo-solver oficial de PASQAL.

Documentación: https://docs.pasqal.com/applicationsolvingtools/qubo/

Backend routing por tamaño del problema:
  n <= 20   ->  EmuFreeBackendV2  (EMU_FREE, estado-vector exacto)
              device=DigitalAnalogDevice  embedding=TriangularEmbedder (custom)
  21-80     ->  EmuMPSBackend     (EMU_MPS, tensor network GPU)
              device=DigitalAnalogDevice  embedding=TriangularEmbedder (custom)

  TriangularEmbedder se usa para TODOS los tamaños porque el embedding
  por defecto (BLaDE) genera registros demasiado dispersos incluso para n ≤ 20.
  Escala=0.77 normalizada garantiza:
    • max_radio < límite del dispositivo para cualquier n ≤ 80
    • min_spacing > 0.71 (5 μm / blockade_radius 7 μm)

Cálculo de escala para n=80 en red 9×9:
  max_radio a escala=1 ≈ 5.45 unidades
  5.45 × 0.77 = 4.20 < 4.55  ✓ radio
  0.77 > 0.71                  ✓ spacing mínimo (5.4 μm)

Requiere:
  pip install qubo-solver pulser-pasqal

Credenciales en .env.pasqal (cargadas vía PasqalCredentials):
  PASQAL_USERNAME=...
  PASQAL_PASSWORD=...
  PASQAL_PROJECT_ID=...
"""
from __future__ import annotations

import time
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

from .problem import QUBOProblem
from .credentials import PasqalCredentials

EMU_FREE_MAX_QUBITS = 20   # exacto hasta 20 qubits
EMU_MPS_MAX_QUBITS  = 100  # tensor network hasta 100 qubits


@dataclass
class QUBOSolverResult:
    best_bitstring: str
    best_selection: List[str]
    best_energy: float
    all_counts: Dict[str, int]
    energy_per_bitstring: Dict[str, float]
    backend: str
    n_shots: int
    n_assets: int
    solve_time_s: float
    metadata: dict = field(default_factory=dict)

    def top_k(self, k: int = 5) -> List[Tuple[str, float, int]]:
        items = sorted(self.energy_per_bitstring.items(), key=lambda x: x[1])
        return [(bs, e, self.all_counts.get(bs, 0)) for bs, e in items[:k]]

    def feasibility_rate(self, budget: int) -> float:
        total    = sum(self.all_counts.values())
        feasible = sum(c for b, c in self.all_counts.items() if b.count("1") == budget)
        return feasible / total if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "backend":        self.backend,
            "n_assets":       self.n_assets,
            "n_shots":        self.n_shots,
            "best_selection": self.best_selection,
            "best_energy":    round(self.best_energy, 6),
            "best_bitstring": self.best_bitstring,
            "solve_time_s":   round(self.solve_time_s, 3),
            "top5":           [(bs, round(e, 6), c) for bs, e, c in self.top_k(5)],
            "metadata":       self.metadata,
        }


def _select_backend_name(n: int) -> str:
    if n <= EMU_FREE_MAX_QUBITS:
        return "EmuFreeBackendV2 (EMU_FREE)"
    return "EmuMPSBackend (EMU_MPS)"


def solve_with_qubo_solver(
    qubo: QUBOProblem,
    creds: PasqalCredentials,
    n_shots: int = 1000,
) -> QUBOSolverResult:
    """
    Resuelve un QUBO usando qubo-solver de PASQAL con backend remoto.

    Selección de backend:
      n <= 20  ->  EmuFreeBackendV2  (exacto)
      n > 20   ->  EmuMPSBackend     (tensor network, 60-100 qubits)

    Nota: qubo-solver requiere que los términos fuera de la diagonal sean
    no negativos para el modo cuántico. Con penalty suficientemente grande
    (>= max|Sigma_ij| / risk_aversion) esto se cumple automáticamente.
    """
    try:
        creds.validate()
    except ValueError as exc:
        raise RuntimeError(f"[qubo_solver] credenciales inválidas: {exc}")

    try:
        import torch
        from qubosolver import QUBOInstance
        from qubosolver.config import (
            SolverConfig, EmbeddingConfig, PasqalCloud, RemoteEmulator,
        )
        from qoolqit import AnalogDevice, DigitalAnalogDevice
        from pulser_pasqal.backends import EmuFreeBackendV2, EmuMPSBackend
    except ImportError as exc:
        raise ImportError(
            f"[qubo_solver] dependencia faltante: {exc}\n"
            "Instala con: pip install qubo-solver pulser-pasqal"
        )

    n = qubo.n
    t0 = time.perf_counter()

    # Simetrizar la matriz QUBO (qubo-solver requiere forma simétrica)
    Q_sym = (qubo.Q + qubo.Q.T) / 2

    # Verificar restricción de términos fuera de diagonal no negativos
    off_diag = Q_sym.copy()
    np.fill_diagonal(off_diag, 0)
    min_off = off_diag.min()
    if min_off < 0:
        warnings.warn(
            f"[qubo_solver] término fuera de diagonal negativo detectado: min={min_off:.4f}. "
            "Considera aumentar el parámetro penalty en el config para que dominen los "
            "términos de restricción. qubo-solver requiere off-diagonal >= 0 para modo cuántico.",
            UserWarning,
        )

    Q_tensor = torch.tensor(Q_sym, dtype=torch.float64)
    instance = QUBOInstance(coefficients=Q_tensor)

    # Conectar a Pasqal Cloud
    connection = PasqalCloud(
        username=creds.username,
        password=creds.password,
        project_id=creds.project_id,
    )

    # Seleccionar backend según tamaño
    backend_type = EmuFreeBackendV2 if n <= EMU_FREE_MAX_QUBITS else EmuMPSBackend
    backend_name = _select_backend_name(n)
    print(f"  [qubo_solver] n={n} qubits  backend={backend_name}  shots={n_shots}")

    backend = RemoteEmulator(
        backend_type=backend_type,
        connection=connection,
        num_shots=n_shots,
    )

    # TriangularEmbedder para TODOS los tamaños.
    #
    # El embedding por defecto (BLaDE) genera registros demasiado dispersos
    # incluso para n pequeños (falla CompilationError en n=20 con EMU_FREE).
    # La red triangular compacta centrada (escala=0.77) garantiza para cualquier n ≤ 80:
    #   max_radio < límite del dispositivo  ✓
    #   min_spacing = 0.77 > 0.71 (5 μm)  ✓
    import math as _math
    import typing

    from qoolqit import Register as _Register
    from qubosolver.pipeline.embedder import BaseEmbedder as _BaseEmbedder

    _SCALE = 0.77   # normalizado en unidades de blockade_radius
    _cols  = _math.ceil(_math.sqrt(n))

    class TriangularEmbedder(_BaseEmbedder):
        """
        Red triangular compacta centrada en el origen.
        escala=0.77  ->  compacto dentro del campo de visión del dispositivo
        para cualquier n ≤ 80.
        """
        @typing.no_type_check
        def embed(self) -> _Register:
            _n = self.instance.coefficients.shape[0]
            positions: dict = {}
            for k in range(_n):
                row = k // _cols
                col = k % _cols
                x = col * _SCALE + (row % 2) * _SCALE / 2
                y = row * _SCALE * _math.sqrt(3) / 2
                positions[f"q{k}"] = (x, y)
            # Centrar en el origen
            cx = sum(v[0] for v in positions.values()) / _n
            cy = sum(v[1] for v in positions.values()) / _n
            centered = {k: (x - cx, y - cy) for k, (x, y) in positions.items()}
            return _Register(centered)

    # Calcular radio máx real (post-centrado) para logging
    _pos = [
        (
            (k % _cols) * _SCALE + ((k // _cols) % 2) * _SCALE / 2,
            (k // _cols) * _SCALE * _math.sqrt(3) / 2,
        )
        for k in range(n)
    ]
    _cx = sum(p[0] for p in _pos) / n
    _cy = sum(p[1] for p in _pos) / n
    _max_r = max(_math.sqrt((x - _cx)**2 + (y - _cy)**2) for x, y in _pos)
    print(f"  [qubo_solver] device=DigitalAnalogDevice  embedding=TriangularEmbedder"
          f"  scale={_SCALE}  max_radius≈{_max_r:.3f}")

    embedding = EmbeddingConfig(embedding_method=TriangularEmbedder)
    config = SolverConfig(
        use_quantum=True,
        backend=backend,
        embedding=embedding,
        device=DigitalAnalogDevice(),
    )

    print(f"  [qubo_solver] enviando trabajo a Pasqal Cloud ...")
    from qubosolver.solver import QuboSolver
    solver = QuboSolver(instance, config)

    # Reintentar si PASQAL Cloud devuelve 503 durante el polling de resultados
    MAX_RETRIES = 5
    RETRY_WAIT  = 30   # segundos entre reintentos
    solution = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            solution = solver.solve()
            break
        except Exception as exc:
            is_503 = "503" in str(exc) or "Service Unavailable" in str(exc)
            if is_503 and attempt < MAX_RETRIES:
                print(f"  [qubo_solver] 503 Service Unavailable — reintento {attempt}/{MAX_RETRIES-1}"
                      f" en {RETRY_WAIT}s ...")
                time.sleep(RETRY_WAIT)
            else:
                raise
    if solution is None:
        raise RuntimeError("[qubo_solver] no se pudo obtener resultado tras todos los reintentos.")

    solve_time = time.perf_counter() - t0
    print(f"  [qubo_solver] completado en {solve_time:.1f}s  status={solution.solution_status}")

    # --- Procesar resultados ---
    # solution.bitstrings: tensor de shape (n_solutions, n)
    # solution.costs: tensor de shape (n_solutions,)
    # solution.counts: tensor o None
    bitstrings_tensor = solution.bitstrings
    costs_tensor      = solution.costs
    counts_tensor     = solution.counts

    n_sol = bitstrings_tensor.shape[0]

    # Construir all_counts y energy_per_bitstring
    all_counts: Dict[str, int] = {}
    energy_per_bitstring: Dict[str, float] = {}

    for idx in range(n_sol):
        bs  = "".join(str(int(b)) for b in bitstrings_tensor[idx].tolist())
        eng = float(costs_tensor[idx]) + qubo.offset
        energy_per_bitstring[bs] = eng
        cnt = int(counts_tensor[idx]) if counts_tensor is not None else 1
        all_counts[bs] = all_counts.get(bs, 0) + cnt

    if not energy_per_bitstring:
        raise RuntimeError("[qubo_solver] no se obtuvieron soluciones.")

    best_bits = min(energy_per_bitstring, key=energy_per_bitstring.__getitem__)
    best_x    = np.array([int(b) for b in best_bits])
    selection = [qubo.symbols[i] for i, xi in enumerate(best_x) if xi == 1]

    return QUBOSolverResult(
        best_bitstring       = best_bits,
        best_selection       = selection,
        best_energy          = energy_per_bitstring[best_bits],
        all_counts           = all_counts,
        energy_per_bitstring = energy_per_bitstring,
        backend              = backend_name,
        n_shots              = n_shots,
        n_assets             = n,
        solve_time_s         = solve_time,
        metadata={
            "solution_status":        str(solution.solution_status),
            "emu_free_max_qubits":    EMU_FREE_MAX_QUBITS,
            "emu_mps_max_qubits":     EMU_MPS_MAX_QUBITS,
            "qubo_off_diag_min":      round(float(min_off), 6),
            "qubo_symmetric":         True,
        },
    )
