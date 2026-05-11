"""
Pasqal neutral-atom quantum solver — n-asset production implementation.

Backend routing by problem size:
  n <= 20  ->  numpy_rydberg   (exact 2^n wavefunction, always available)
  n <= 100 ->  pulser_local    (QutipEmulator, requires pulser-simulation)
  n <= 100 ->  pulser_cloud    (Pasqal Cloud EMU_FREE, requires .env.pasqal)
  any n    ->  sa_hybrid       (simulated annealing, always available)

Credentials for pulser_cloud are loaded from .env.pasqal via credentials.py.
"""
from __future__ import annotations

import itertools
import math
import time
import warnings
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
from scipy.linalg import expm
from scipy.optimize import dual_annealing

from .problem import QUBOProblem
from .credentials import PasqalCredentials

# ---------------------------------------------------------------------------
# Hardware constants (Pasqal Fresnel QPU, Rb87 |70S_1/2>)
# ---------------------------------------------------------------------------
C6_RYDBERG        = 862_690.0
BLOCKADE_RADIUS   = 7.0
LATTICE_SPACING   = 10.5
OMEGA_MAX         = 2 * math.pi * 1.5  # 9.42 rad/us — 75% of AnalogDevice max_amp (12.566) to account for output modulation
DELTA_START       = 2 * math.pi * -5
DELTA_END         = 2 * math.pi *  5
T_RAMP_US         = 0.5                # us — 500 ns, multiple of clock_period (4 ns)
T_HOLD_US         = 2.0
TOTAL_TIME_US     = 2 * T_RAMP_US + T_HOLD_US

NUMPY_MAX_QUBITS  = 20
PULSER_MAX_QUBITS = 100


# ---------------------------------------------------------------------------
# Register geometry
# ---------------------------------------------------------------------------

def _build_register(n: int, spacing: float = LATTICE_SPACING) -> np.ndarray:
    cols = max(1, math.ceil(math.sqrt(n)))
    positions = []
    for k in range(n):
        row, col = k // cols, k % cols
        x = col * spacing + (row % 2) * spacing / 2
        y = row * spacing * math.sqrt(3) / 2
        positions.append([x, y])
    return np.array(positions[:n], dtype=float)


# ---------------------------------------------------------------------------
# NumPy exact Rydberg simulator  (n <= 20)
# ---------------------------------------------------------------------------

def _kron_op(op: np.ndarray, site: int, n: int) -> np.ndarray:
    eye = np.eye(2, dtype=complex)
    ops = [eye if k != site else op.astype(complex) for k in range(n)]
    out = ops[0]
    for o in ops[1:]:
        out = np.kron(out, o)
    return out


def _rydberg_hamiltonian(positions: np.ndarray, omega: float, delta: float) -> np.ndarray:
    n = len(positions)
    sx   = np.array([[0, 1], [1, 0]], dtype=complex)
    n_op = np.array([[0, 0], [0, 1]], dtype=complex)
    H = np.zeros((2**n, 2**n), dtype=complex)
    for i in range(n):
        H += (omega / 2) * _kron_op(sx, i, n)
        H -= delta       * _kron_op(n_op, i, n)
    for i, j in itertools.combinations(range(n), 2):
        r = max(np.linalg.norm(positions[i] - positions[j]), 0.1)
        U = C6_RYDBERG / r**6
        H += U * (_kron_op(n_op, i, n) @ _kron_op(n_op, j, n))
    return H


def _simulate_numpy(
    positions: np.ndarray,
    n_steps: int = 100,
    n_shots: int = 1000,
    omega_max: float = OMEGA_MAX,
    delta_start: float = DELTA_START,
    delta_end: float = DELTA_END,
    seed: int = 42,
) -> Dict[str, int]:
    rng = np.random.default_rng(seed)
    n   = len(positions)
    dim = 2**n
    dt  = TOTAL_TIME_US / n_steps
    t_ramp = T_RAMP_US
    t_hold = T_RAMP_US + T_HOLD_US

    psi = np.zeros(dim, dtype=complex)
    psi[0] = 1.0

    for step in range(n_steps):
        t = step * dt
        if   t < t_ramp: omega = omega_max * t / t_ramp
        elif t < t_hold: omega = omega_max
        else:            omega = omega_max * (1 - (t - t_hold) / t_ramp)
        frac  = min(t / TOTAL_TIME_US, 1.0)
        delta = delta_start + frac * (delta_end - delta_start)
        H     = _rydberg_hamiltonian(positions, omega, delta)
        psi   = expm(-1j * H * dt) @ psi

    probs = np.abs(psi)**2
    probs = np.clip(probs.real, 0, None)
    probs /= probs.sum()
    indices = rng.choice(dim, size=n_shots, p=probs)
    counts: Dict[str, int] = {}
    for idx in indices:
        b = format(idx, f"0{n}b")
        counts[b] = counts.get(b, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Simulated Annealing hybrid  (any n)
# ---------------------------------------------------------------------------

def _simulate_sa(
    qubo: QUBOProblem,
    n_shots: int = 1000,
    seed: int = 42,
    sa_maxiter: int = 10_000,
) -> Dict[str, int]:
    rng   = np.random.default_rng(seed)
    n     = qubo.n
    Q_sym = (qubo.Q + qubo.Q.T) / 2

    def objective(x: np.ndarray) -> float:
        return float(x @ Q_sym @ x) + qubo.offset

    bounds      = [(0.0, 1.0)] * n
    counts: Dict[str, int] = {}
    n_restarts  = max(10, n_shots // 10)

    for _ in range(n_restarts):
        res = dual_annealing(
            objective, bounds,
            seed=int(rng.integers(0, 2**31)),
            maxiter=sa_maxiter,
            x0=rng.uniform(0, 1, n),
        )
        b = "".join(str(int(xi > 0.5)) for xi in res.x)
        counts[b] = counts.get(b, 0) + max(1, n_shots // n_restarts)

    return counts


# ---------------------------------------------------------------------------
# Pulser local emulator  (n <= 100)
# ---------------------------------------------------------------------------

def _simulate_pulser_local(
    positions: np.ndarray,
    n_shots: int,
    omega_max: float,
    delta_start: float,
    delta_end: float,
) -> Optional[Dict[str, int]]:
    try:
        import pulser
        from pulser import Register, Sequence
        from pulser.devices import MockDevice
        from pulser.waveforms import RampWaveform, ConstantWaveform
        from pulser_simulation import QutipEmulator

        coords = {f"q{i}": tuple(float(v) for v in positions[i]) for i in range(len(positions))}
        reg    = Register(coords)
        seq    = Sequence(reg, MockDevice)
        seq.declare_channel("global", "rydberg_global")

        t_ramp_ns = int(T_RAMP_US * 1000)
        t_hold_ns = int(T_HOLD_US * 1000)

        # Adiabatic ramp: delta +|end| -> 0 -> -|end|
        # Starting with positive detuning favors ground state, ending negative
        # favors selective excitation — produces feasible low-excitation states
        seq.add(pulser.Pulse(
            amplitude=RampWaveform(t_ramp_ns, 0, omega_max),
            detuning=ConstantWaveform(t_ramp_ns, delta_end),
            phase=0,
        ), "global")
        seq.add(pulser.Pulse(
            amplitude=ConstantWaveform(t_hold_ns, omega_max),
            detuning=RampWaveform(t_hold_ns, delta_end, delta_start),
            phase=0,
        ), "global")
        seq.add(pulser.Pulse(
            amplitude=RampWaveform(t_ramp_ns, omega_max, 0),
            detuning=ConstantWaveform(t_ramp_ns, delta_start),
            phase=0,
        ), "global")

        sim = QutipEmulator.from_sequence(seq)
        res = sim.run()
        raw = res.sample_final_state(n_shots)
        return {k: int(v) for k, v in raw.items()}

    except ImportError:
        return None
    except Exception as exc:
        warnings.warn(f"[pulser_local] {exc}")
        return None


# ---------------------------------------------------------------------------
# Pasqal Cloud EMU_FREE  (n <= 100)
# Credentials loaded from .env.pasqal via PasqalCredentials
# ---------------------------------------------------------------------------

def _simulate_pulser_cloud(
    positions: np.ndarray,
    n_shots: int,
    omega_max: float,
    delta_start: float,
    delta_end: float,
    creds: PasqalCredentials,
    poll_interval: float = 5.0,
    timeout: float = 300.0,
) -> Optional[Dict[str, int]]:
    """
    Submit job to Pasqal Cloud EMU_FREE emulator.
    Credentials come from .env.pasqal (username, password, project_id).
    """
    try:
        creds.validate()
    except ValueError as exc:
        warnings.warn(f"[pasqal_cloud] {exc}")
        return None

    try:
        import pulser
        from pulser import Register, Sequence
        from pulser.devices import MockDevice
        from pulser.waveforms import RampWaveform, ConstantWaveform
        from pasqal_cloud import SDK, EmulatorType, BaseConfig

        coords = {f"q{i}": tuple(float(v) for v in positions[i]) for i in range(len(positions))}
        reg    = Register(coords)
        seq    = Sequence(reg, MockDevice)
        seq.declare_channel("global", "rydberg_global")

        t_ramp_ns = int(T_RAMP_US * 1000)
        t_hold_ns = int(T_HOLD_US * 1000)

        # Adiabatic ramp: delta +|end| -> 0 -> -|end|
        seq.add(pulser.Pulse(
            amplitude=RampWaveform(t_ramp_ns, 0, omega_max),
            detuning=ConstantWaveform(t_ramp_ns, delta_end),
            phase=0,
        ), "global")
        seq.add(pulser.Pulse(
            amplitude=ConstantWaveform(t_hold_ns, omega_max),
            detuning=RampWaveform(t_hold_ns, delta_end, delta_start),
            phase=0,
        ), "global")
        seq.add(pulser.Pulse(
            amplitude=RampWaveform(t_ramp_ns, omega_max, 0),
            detuning=ConstantWaveform(t_ramp_ns, delta_start),
            phase=0,
        ), "global")

        print(f"  [pasqal_cloud] connecting as {creds.username} ...")
        sdk = SDK(
            username=creds.username,
            password=creds.password,
            project_id=creds.project_id,
        )
        batch = sdk.create_batch(
            serialized_sequence=seq.to_abstract_repr(),
            jobs=[{"runs": n_shots}],
            device_type=EmulatorType.EMU_FREE,
            configuration=BaseConfig(),
        )
        print(f"  [pasqal_cloud] job submitted  batch_id={batch.id}")

        elapsed = 0.0
        while elapsed < timeout:
            time.sleep(poll_interval)
            elapsed += poll_interval
            batch.refresh()
            print(f"  [pasqal_cloud] status={batch.status}  ({elapsed:.0f}s)")
            if batch.status == "DONE":
                break
            if batch.status in ("ERROR", "CANCELED"):
                warnings.warn(f"[pasqal_cloud] job ended with status={batch.status}")
                return None

        if batch.status != "DONE":
            warnings.warn("[pasqal_cloud] timeout waiting for results")
            return None

        raw = batch.ordered_jobs[0].result
        return {k: int(v) for k, v in raw.items()} if isinstance(raw, dict) else None

    except ImportError as exc:
        warnings.warn(f"[pasqal_cloud] missing dependency: {exc} — run: pip install pasqal-cloud pulser")
        return None
    except Exception as exc:
        warnings.warn(f"[pasqal_cloud] unexpected error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class PasqalSolverResult:
    best_bitstring: str
    best_selection: List[str]
    best_energy: float
    all_counts: Dict[str, int]
    energy_per_bitstring: Dict[str, float]
    register_positions: np.ndarray
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
            "backend":              self.backend,
            "n_assets":             self.n_assets,
            "n_shots":              self.n_shots,
            "best_selection":       self.best_selection,
            "best_energy":          round(self.best_energy, 6),
            "best_bitstring":       self.best_bitstring,
            "solve_time_s":         round(self.solve_time_s, 3),
            "top5":                 [(bs, round(e, 6), c) for bs, e, c in self.top_k(5)],
            "register_positions_um": self.register_positions.tolist(),
            "metadata":             self.metadata,
        }


# ---------------------------------------------------------------------------
# Main solver
# ---------------------------------------------------------------------------

class PasqalNeutralAtomSolver:
    """
    Production portfolio optimisation solver supporting n assets.

    Backend auto-routing:
      n <= 20    ->  numpy_rydberg   (exact, no dependencies)
      n <= 100   ->  pulser_local    (QutipEmulator, if installed)
      n <= 100   ->  pulser_cloud    (Pasqal Cloud, credentials from .env.pasqal)
      any n      ->  sa_hybrid       (scipy dual_annealing, always available)

    Credentials file (.env.pasqal):
      PASQAL_USERNAME=tu@email.com
      PASQAL_PASSWORD=tu_password
      PASQAL_PROJECT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
    """

    def __init__(
        self,
        n_shots:            int   = 1000,
        backend:            str   = "auto",
        omega_max:          float = OMEGA_MAX,
        delta_start:        float = DELTA_START,
        delta_end:          float = DELTA_END,
        lattice_spacing_um: float = LATTICE_SPACING,
        blockade_radius_um: float = BLOCKADE_RADIUS,
        n_time_steps:       int   = 100,
        sa_maxiter:         int   = 10_000,
        seed:               int   = 42,
        use_pulser:         bool  = True,
        # Legacy aliases (kept for backward compatibility)
        cloud_token:        str   = "",
        pasqal_cloud_token: str   = "",
        project_id:         str   = "",
    ):
        self.n_shots            = n_shots
        self.backend            = backend
        self.omega_max          = omega_max
        self.delta_start        = delta_start
        self.delta_end          = delta_end
        self.lattice_spacing_um = lattice_spacing_um
        self.blockade_radius_um = blockade_radius_um
        self.n_time_steps       = n_time_steps
        self.sa_maxiter         = sa_maxiter
        self.seed               = seed
        self.use_pulser         = use_pulser

        # Load credentials lazily — only when pulser_cloud is actually needed
        self._creds: Optional[PasqalCredentials] = None

    def _get_credentials(self) -> PasqalCredentials:
        if self._creds is None:
            self._creds = PasqalCredentials.load()
        return self._creds

    def _select_backend(self, n: int) -> str:
        if self.backend != "auto":
            return self.backend
        # Check if credentials are available without printing noise
        creds = self._get_credentials()
        if creds.is_complete() and n <= PULSER_MAX_QUBITS:
            return "pulser_cloud"
        if self.use_pulser and n <= PULSER_MAX_QUBITS:
            return "pulser_local"
        if n <= NUMPY_MAX_QUBITS:
            return "numpy_rydberg"
        return "sa_hybrid"

    def solve(self, qubo: QUBOProblem) -> PasqalSolverResult:
        n  = qubo.n
        t0 = time.perf_counter()
        selected = self._select_backend(n)
        print(f"  [solver] n={n} assets  backend={selected}")

        positions = _build_register(n, self.lattice_spacing_um)
        counts: Optional[Dict[str, int]] = None
        actual_backend = selected

        if selected == "pulser_cloud":
            counts = _simulate_pulser_cloud(
                positions, self.n_shots, self.omega_max,
                self.delta_start, self.delta_end,
                self._get_credentials(),
            )
            if counts is None:
                selected = "pulser_local"
                print("  [solver] pulser_cloud failed -> pulser_local")

        if selected == "pulser_local" and counts is None:
            counts = _simulate_pulser_local(
                positions, self.n_shots, self.omega_max,
                self.delta_start, self.delta_end,
            )
            if counts is None:
                selected = "numpy_rydberg" if n <= NUMPY_MAX_QUBITS else "sa_hybrid"
                print(f"  [solver] pulser_local not available -> {selected}")

        if selected == "numpy_rydberg" and counts is None:
            if n > NUMPY_MAX_QUBITS:
                warnings.warn(
                    f"n={n} exceeds numpy_rydberg limit ({NUMPY_MAX_QUBITS}). "
                    "Routing to sa_hybrid. For quantum emulation at this scale, "
                    "install pulser-simulation or add credentials to .env.pasqal.",
                    UserWarning, stacklevel=2,
                )
                selected = "sa_hybrid"
            else:
                counts = _simulate_numpy(
                    positions, self.n_time_steps, self.n_shots,
                    self.omega_max, self.delta_start, self.delta_end, self.seed,
                )
                actual_backend = "numpy_rydberg"

        if selected == "sa_hybrid" and counts is None:
            counts = _simulate_sa(qubo, self.n_shots, self.seed, self.sa_maxiter)
            actual_backend = "sa_hybrid"

        if counts is None:
            raise RuntimeError("All backends failed — check configuration.")

        energy_map: Dict[str, float] = {
            bits: qubo.evaluate(np.array([int(b) for b in bits], dtype=float))
            for bits in counts if len(bits) == n
        }
        if not energy_map:
            raise RuntimeError("No valid bitstrings returned by solver.")

        best_bits = min(energy_map, key=energy_map.__getitem__)
        best_x    = np.array([int(b) for b in best_bits], dtype=float)
        selection = [qubo.symbols[i] for i, xi in enumerate(best_x) if xi == 1]

        return PasqalSolverResult(
            best_bitstring      = best_bits,
            best_selection      = selection,
            best_energy         = energy_map[best_bits],
            all_counts          = counts,
            energy_per_bitstring= energy_map,
            register_positions  = positions,
            backend             = actual_backend,
            n_shots             = self.n_shots,
            n_assets            = n,
            solve_time_s        = time.perf_counter() - t0,
            metadata={
                "omega_max_rad_per_us":  self.omega_max,
                "delta_start_rad_per_us": self.delta_start,
                "delta_end_rad_per_us":  self.delta_end,
                "lattice_spacing_um":    self.lattice_spacing_um,
                "n_time_steps":          self.n_time_steps,
                "c6_rydberg":            C6_RYDBERG,
                "numpy_max_qubits":      NUMPY_MAX_QUBITS,
                "pulser_max_qubits":     PULSER_MAX_QUBITS,
            },
        )
