# Crypto Portfolio QOpt

Quantum portfolio optimisation for crypto assets using Pasqal neutral-atom hardware.

Ingests real market data from CoinGecko (Go), formulates a Markowitz mean-variance QUBO, and solves it via [`qubo-solver`](https://docs.pasqal.com/applicationsolvingtools/qubo/) — PASQAL's official solver library — submitted to Pasqal Cloud.

---

## Architecture

```
ingest (Go)          data.py              problem.py           solver_qubo.py
CoinGecko API   →   PortfolioDataset  →  QUBO n×n         →  qubo-solver (PASQAL)
market_snapshot      mu, Sigma            Markowitz              EmuFreeBackendV2 (n≤20)
     .json           covariance           penalty budget         EmuMPSBackend    (n≤80)
                                              ↓
                                         benchmark.py  →  results/logs/*.json
                                         exact / greedy / Pasqal comparison
```

**Backend routing** (automático por tamaño):

| n activos (= qubits) | Backend | Device | Notas |
|----------------------|---------|--------|-------|
| ≤ 20 | `EmuFreeBackendV2` (EMU_FREE) | `DigitalAnalogDevice` | Estado-vector exacto |
| 21 – 80 | `EmuMPSBackend` (EMU_MPS) | `AnalogDevice` | Tensor network GPU, embedding greedy |
| > 80 | ❌ no soportado | — | Excede el límite de átomos del hardware |

---

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Git

That's it. No local Python or Go installation required.

---

## Quickstart

### 1. Clone

```bash
git clone https://github.com/aaroon2895/crypto-portfolio-qopt.git
cd crypto-portfolio-qopt
```

### 2. Build images

```bash
docker compose build
```

### 3. Ingest market data (CoinGecko → JSON)

```bash
docker compose run --rm ingest
```

Fetches 30 days of OHLCV data for BTC, ETH, SOL and writes it to `data/raw/market_snapshot.json`.

> Note: the free CoinGecko tier rate-limits to ~10 req/min. The ingest takes ~60 seconds and retries automatically on 429.

### 4. Run experiment

```bash
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_mean_variance.yaml \
  --persist \
  --output-dir results/logs
```

Expected output (without Pasqal Cloud credentials):
```
[solver] n=3 assets  backend=numpy_rydberg
Pasqal (numpy_rydberg)  ->  ['BTC', 'ETH']  E=-0.002545
gap vs optimal: +0.000000
```

### 5. Run tests

```bash
docker compose run --rm test
```

---

## Pasqal Cloud (optional — runs on real quantum emulator)

To submit jobs to Pasqal Cloud EMU_FREE (free tier, no credit card required):

**1. Create account**

Go to [portal.pasqal.cloud](https://portal.pasqal.cloud) and sign up.

**2. Get your Project ID**

Portal → user icon (top right) → Projects → copy the UUID.

**3. Create credentials file**

```bash
cp .env.pasqal.example .env.pasqal
```

Edit `.env.pasqal`:

```
PASQAL_USERNAME=tu@email.com
PASQAL_PASSWORD=tu_password
PASQAL_PROJECT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> `.env.pasqal` is in `.gitignore` — it will never be committed.

**4. Run**

```bash
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_mean_variance.yaml \
  --persist \
  --output-dir results/logs
```

Expected output with credentials:
```
[credentials] loaded from /app/.env.pasqal
[solver] n=3 assets  backend=pulser_cloud
[pasqal_cloud] connecting as tu@email.com ...
[pasqal_cloud] job submitted  batch_id=xxxxxxxx
[pasqal_cloud] status=DONE  (60s)
Pasqal (pulser_cloud)  ->  ['BTC', 'ETH']  E=-0.002545
gap vs optimal: +0.000000
```

---

## Límite de átomos — cómo no exceder los 80 qubits

> **Regla clave:** el número de activos en el dataset = número de qubits.
> El hardware de PASQAL soporta un máximo de **80 átomos**.

### Los dos parámetros que controlan el tamaño

```yaml
# En configs/experiments/tu_experimento.yaml

data:
  path: data/raw/market_snapshot_n80.json  # ← número de activos en el JSON = n qubits

problem:
  constraints:
    budget: 20    # ← cuántos activos SELECCIONAR (no afecta los qubits, solo la restricción)
    penalty: 80.0 # ← recomendado: penalty ≈ n  (mantiene off-diagonal ≥ 0 para el solver cuántico)
```

| Parámetro | Efecto en qubits | Regla |
|-----------|-----------------|-------|
| Activos en el dataset | **Directo** — 1 activo = 1 qubit | Mantener ≤ 80 |
| `budget` | Ninguno — solo define cuántos seleccionar | Recomendado: `n / 4` |
| `penalty` | Ninguno — solo fuerza la restricción | Recomendado: ≥ `n` |

### Experimentos listos para usar

| Config | Activos (qubits) | Budget | Backend automático | Dataset |
|--------|-----------------|--------|--------------------|---------|
| `pasqal_test_n3.yaml` | **3** | 1 | EMU_FREE (exacto) | `market_snapshot.json` (BTC/ETH/SOL) |
| `pasqal_test_n10.yaml` | **10** | 3 | EMU_FREE (exacto) | `market_snapshot_n10.json` |
| `pasqal_n80.yaml` | **80** | 20 | EMU_MPS (tensor network) | `market_snapshot_n80.json` |

### Comandos de ejecución

```bash
# Siempre hacer build antes si cambiaste código
docker compose build app

# Prueba pequeña — 3 qubits, EMU_FREE
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_test_n3.yaml \
  --persist --output-dir results/logs

# Prueba mediana — 10 qubits, EMU_FREE
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_test_n10.yaml \
  --persist --output-dir results/logs

# Experimento completo — 80 qubits, EMU_MPS
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_n80.yaml \
  --persist --output-dir results/logs
```

### Cómo crear un experimento propio (sin exceder 80)

1. **Prepara el dataset** — el JSON debe tener ≤ 80 activos:

```bash
# Ejemplo: 40 activos personalizados
docker compose run --rm ingest \
  --symbols BTC,ETH,BNB,SOL,XRP,ADA,AVAX,DOGE,DOT,LINK,\
MATIC,UNI,LTC,ATOM,XLM,ETC,HBAR,APT,ARB,NEAR,\
INJ,ALGO,AAVE,SAND,MANA,AXS,THETA,EOS,EGLD,XTZ,\
FLOW,CHZ,CAKE,SNX,ZEC,DASH,BAT,ENJ,CRV,COMP \
  --days 90 --out /app/data/raw/market_snapshot_n40.json
```

2. **Crea el config YAML** (copia y ajusta `pasqal_n80.yaml`):

```yaml
experiment_name: mi_experimento_40_activos

data:
  source: json
  path: data/raw/market_snapshot_n40.json   # 40 activos → 40 qubits ✓

problem:
  type: mean_variance_binary
  risk_aversion: 0.5
  constraints:
    budget: 10      # seleccionar 10 de 40
    penalty: 40.0   # penalty ≈ n

pasqal:
  use_qubo_solver: true
  n_shots: 2000     # EMU_MPS se selecciona automáticamente (n=40 > 20)
```

3. **Ejecuta:**

```bash
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/mi_experimento_40_activos.yaml \
  --persist --output-dir results/logs
```

### Qué pasa si excedes 80 átomos

El solver lanzará un error de compilación antes de enviar el job a la nube:

```
CompilationError: The register's maximum radial distance went over the maximum value allowed.
```

Esto sucede porque el registro físico de átomos no cabe en el campo de visión del dispositivo.
**Solución:** reduce el número de activos en el dataset a ≤ 80.

---

## Custom symbols (ingest)

Edit `docker-compose.yml`:

```yaml
command:
  ["--provider", "coingecko",
   "--symbols", "BTC,ETH,SOL,BNB,ADA",   # ← add symbols here
   "--vs-currency", "usd",
   "--days", "30",
   "--out", "/app/data/raw/market_snapshot.json"]
```

Then:

```bash
docker compose run --rm ingest
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_mean_variance.yaml \
  --persist --output-dir results/logs
```

---

## Results

JSON results are saved to `results/logs/<experiment_name>.json`:

```json
{
  "experiment": "pasqal_mean_variance_btc_eth_sol",
  "symbols": ["BTC", "ETH", "SOL"],
  "optimal_selection": ["BTC", "ETH"],
  "optimal_energy": -0.002545,
  "pasqal": {
    "backend": "pulser_cloud",
    "best_selection": ["BTC", "ETH"],
    "best_energy": -0.002545,
    "gap vs optimal": 0.0
  }
}
```

---

## Project structure

```
.
├── cmd/ingest/            Go ingest entrypoint
├── internal/ingest/       CoinGecko connector, OHLCV pipeline
├── src/qportfolio/qopt/   Python quantum stack
│   ├── data.py            PortfolioDataset — loads JSON or in-memory config
│   ├── problem.py         MeanVarianceBinaryProblem → QUBO n×n
│   ├── solver_qubo.py     Solver oficial PASQAL (qubo-solver) — EmuFree / EmuMPS
│   ├── solver_pasqal.py   Solver legacy Pulser (fallback, use_qubo_solver: false)
│   ├── solver_classical.py Greedy + exact brute-force (reference)
│   ├── benchmark.py       Pipeline: data → QUBO → solve → report
│   └── credentials.py     Loads .env.pasqal with priority chain
├── scripts/
│   └── run_experiment.py  CLI entrypoint
├── configs/experiments/
│   ├── pasqal_test_n3.yaml    3 qubits  — EMU_FREE
│   ├── pasqal_test_n10.yaml   10 qubits — EMU_FREE
│   └── pasqal_n80.yaml        80 qubits — EMU_MPS  ← límite máximo
├── data/raw/
│   ├── market_snapshot.json       3 activos  (BTC/ETH/SOL, datos reales)
│   ├── market_snapshot_n10.json   10 activos (sintético GBM)
│   └── market_snapshot_n80.json   80 activos (sintético GBM)
├── tests/                 pytest suite
├── Dockerfile.python      Python app image
├── Dockerfile.go          Go ingest image
├── docker-compose.yml
├── .env.pasqal.example    Credentials template
└── requirements.txt
```

---

## Environment variables

All credentials are read from `.env.pasqal` (highest priority: explicit args → env vars → file):

| Variable | Description |
|----------|-------------|
| `PASQAL_USERNAME` | Pasqal Cloud account email |
| `PASQAL_PASSWORD` | Pasqal Cloud password |
| `PASQAL_PROJECT_ID` | Project UUID from portal.pasqal.cloud |

Can also be passed at runtime:

```bash
docker compose run --rm \
  -e PASQAL_USERNAME=tu@email.com \
  -e PASQAL_PASSWORD=tu_password \
  -e PASQAL_PROJECT_ID=xxxxxxxx \
  app python scripts/run_experiment.py --config configs/experiments/pasqal_mean_variance.yaml
```

---

## Hardware limits (Pasqal Fresnel QPU / EMU_MPS)

| Parámetro | Valor | Impacto en el código |
|-----------|-------|----------------------|
| **Máx. átomos** | **80** | Dataset debe tener ≤ 80 activos |
| Máx. Ω (Rabi) | 12.566 rad/μs (2π × 2 MHz) | `qubo-solver` respeta esto automáticamente |
| Máx. \|δ\| (detuning) | 125.66 rad/μs | Ídem |
| Máx. duración secuencia | 6000 ns | Ídem |
| C₆ (Rb87 \|70S₁/₂⟩) | 862,690 rad·μs⁻¹·μm⁶ | Constante de interacción Rydberg |
| Radio máx. registro (Fresnel) | ~32 μm | Para n > 20 se usa `AnalogDevice` (60 μm) |

`qubo-solver` gestiona automáticamente el embedding de los átomos dentro de estas restricciones. El único parámetro que debes controlar es **el número de activos en el dataset (≤ 80)**.
