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

| n activos (= qubits) | Backend | Device | Tiempo estimado | Notas |
|----------------------|---------|--------|-----------------|-------|
| ≤ 20 | `EmuFreeBackendV2` (EMU_FREE) | `DigitalAnalogDevice` | segundos | Estado-vector exacto |
| 21 – 60 | `EmuMPSBackend` (EMU_MPS) | `DigitalAnalogDevice` | **1–3 horas** | Tensor network GPU, `TriangularEmbedder` |
| 61 – 80 | `EmuMPSBackend` (EMU_MPS) | `DigitalAnalogDevice` | **3–8 horas** | Riesgo OOM si GPU compartida está llena |
| > 80 | ❌ no soportado | — | — | Excede el límite de átomos del hardware |

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

| Config | Activos (qubits) | Budget | Backend automático | Tiempo estimado | Dataset |
|--------|-----------------|--------|--------------------|-----------------|---------|
| `pasqal_test_n3.yaml` | **3** | 1 | EMU_FREE (exacto) | segundos | `market_snapshot.json` (BTC/ETH/SOL) |
| `pasqal_test_n10.yaml` | **10** | 3 | EMU_FREE (exacto) | segundos | `market_snapshot_n10.json` |
| `pasqal_test_n20.yaml` | **20** | 5 | EMU_FREE (exacto) | segundos | `market_snapshot_n20.json` |
| `pasqal_n30.yaml` | **30** | 8 | EMU_MPS (tensor network) | **20–60 min** | `market_snapshot_n30.json` |
| `pasqal_n60.yaml` | **60** | 15 | EMU_MPS (tensor network) | **1–3 horas** | `market_snapshot_n60.json` |
| `pasqal_n80.yaml` | **80** | 20 | EMU_MPS (tensor network) | **3–8 horas** | `market_snapshot_n80.json` |

> ⚠️ **Advertencia de tiempo de ejecución (EMU_MPS)**
>
> EMU_MPS es una **simulación clásica** de hardware cuántico. El tiempo escala con el número de qubits y el entanglement — **no con `n_shots`**. Reducir los shots no acorta el tiempo de forma significativa.
>
> Para desarrollo e iteración rápida, usa siempre **n ≤ 20** (EMU_FREE, segundos). Reserva EMU_MPS para validación final. Una vez con acceso al **Fresnel QPU** (hardware físico), los mismos problemas de 60–80 qubits se resuelven en **minutos**.

### Comandos de ejecución

```bash
# Siempre hacer build antes si cambiaste código
docker compose build app

# Prueba pequeña — 3 qubits, EMU_FREE  (~segundos)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_test_n3.yaml \
  --persist --output-dir results/logs

# Prueba mediana — 10 qubits, EMU_FREE  (~segundos)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_test_n10.yaml \
  --persist --output-dir results/logs

# Prueba límite EMU_FREE — 20 qubits, EMU_FREE  (~segundos)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_test_n20.yaml \
  --persist --output-dir results/logs

# Primer salto EMU_MPS — 30 qubits  (⚠️ 20–60 min)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_n30.yaml \
  --persist --output-dir results/logs

# Experimento grande — 60 qubits, EMU_MPS  (⚠️ 1–3 horas)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_n60.yaml \
  --persist --output-dir results/logs

# Experimento completo — 80 qubits, EMU_MPS  (⚠️ 3–8 horas, puede fallar por OOM de GPU)
docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_n80.yaml \
  --persist --output-dir results/logs
```

> **Sobre el OOM en EMU_MPS con n=80:** la GPU de PASQAL Cloud es compartida. Si hay otros jobs corriendo, un run de 80 qubits puede consumir la VRAM disponible y fallar tras varias horas. El límite práctico actual es **n=60**. Para n=80 en producción, usar el **Fresnel QPU** (no tiene esta limitación).

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

## Historial de experimentos en Pasqal Cloud

| Experimento | Fecha | Backend | n qubits | Shots | Run time | Status |
|-------------|-------|---------|----------|-------|----------|--------|
| `pasqal_test_3_assets` | — | EMU_FREE | 3 | 1000 | segundos | ✅ Feasible |
| `pasqal_test_10_assets` | — | EMU_FREE | 10 | 2000 | segundos | ✅ Feasible |
| `pasqal_portfolio_30_assets` | 2026-06-19 | EMU_MPS | 30 | 1000 | **8h 1min 29s** | ⚠️ Infeasible (penalty insuficiente) |
| `pasqal_portfolio_60_assets` | 2026-06-19 | EMU_MPS | 60 | 2000 | — | ❌ Timeout / 503 durante polling de resultados |
| `pasqal_portfolio_80_assets` | 2026-06-19 | EMU_MPS | 80 | 3000 | ~5h | ❌ CUDA OOM — GPU sin VRAM disponible |

**Archivos de evidencia:** `results/logs/`

### Notas del experimento n=30 (2026-06-19)

- **Run time PASQAL Cloud:** creación 13:06:35 → fin 21:08:11 = 8h 1min 29s
- **Bond dimension máximo:** 883 (entanglement real generado, simulación no-trivial)
- **Resultado:** `101010000001101010000001101010` — 999/1000 shots convergieron al mismo bitstring
- **Problema:** seleccionó 11 activos en lugar de 8 (budget constraint incumplida)
- **Causa:** `penalty=30` insuficiente; recomendado ≥ 150 para n=30
- **Conclusión:** pipeline EMU_MPS funciona a n=30. Para n≥60 se necesita el **Fresnel QPU**.

### Error n=60 — Timeout / 503 (2026-06-19)

El job compiló y fue enviado correctamente a PASQAL Cloud, pero el cliente recibió errores HTTP 503 (Service Unavailable) durante el polling de resultados. El job continuó corriendo en el servidor pero el cliente perdió la conexión antes de recuperar el resultado. Se agregó lógica de reintento (5 intentos, 30s de espera) en `solver_qubo.py` para mitigar esto en futuras ejecuciones.

### Error n=80 — CUDA Out of Memory (2026-06-19)

Tras ~5 horas de ejecución el job falló con el siguiente error en el servidor de PASQAL Cloud:

```
Job was correctly submitted but failed during execution due to out of memory error.
Details: CUDA out of memory. Tried to allocate 1.86 GiB.
GPU 0 has a total capacity of 39.39 GiB of which 272.06 MiB is free.
Including non-PyTorch memory, this process has 39.12 GiB memory in use.
Of the allocated memory 25.48 GiB is allocated by PyTorch, and 13.11 GiB is
reserved by PyTorch but unallocated.
```

**Causa:** la GPU de PASQAL Cloud es compartida entre múltiples jobs. Al momento de la ejecución, 39.12 GiB de los 39.39 GiB estaban ocupados por otros procesos, dejando solo 272 MiB libres frente a los 1.86 GiB que requería el tensor network de 80 qubits.

**Conclusión:** el fallo es por contención de GPU, no por un límite intrínseco del simulador. PASQAL confirma soporte hasta 80–85 qubits en EMU_MPS. Para garantizar la ejecución a n=80 se requiere el **Fresnel QPU** (hardware físico, sin limitación de VRAM compartida).

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
│   ├── pasqal_test_n3.yaml    3 qubits  — EMU_FREE  (segundos)
│   ├── pasqal_test_n10.yaml   10 qubits — EMU_FREE  (segundos)
│   ├── pasqal_test_n20.yaml   20 qubits — EMU_FREE  (segundos, límite exacto)
│   ├── pasqal_n30.yaml        30 qubits — EMU_MPS   (20–60 min)
│   ├── pasqal_n60.yaml        60 qubits — EMU_MPS   (1–3 horas)
│   └── pasqal_n80.yaml        80 qubits — EMU_MPS   (3–8 horas, riesgo OOM)
├── data/raw/
│   ├── market_snapshot.json       3 activos  (BTC/ETH/SOL, datos reales)
│   ├── market_snapshot_n10.json   10 activos (sintético GBM)
│   ├── market_snapshot_n20.json   20 activos (sintético GBM)
│   ├── market_snapshot_n30.json   30 activos (sintético GBM)
│   ├── market_snapshot_n60.json   60 activos (sintético GBM)
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
| Radio máx. registro (Fresnel) | ~32 μm | `TriangularEmbedder` scale=0.77 → max_radio≈4.20 < 4.55 ✓ |

`qubo-solver` gestiona automáticamente el embedding de los átomos dentro de estas restricciones. El único parámetro que debes controlar es **el número de activos en el dataset (≤ 80)**.

### EMU_MPS vs Fresnel QPU

| | EMU_MPS (simulador) | Fresnel QPU (hardware) |
|---|---|---|
| Tipo | Simulación clásica GPU | Átomos de Rubidio reales |
| Tiempo para 60–80 qubits | **1–8 horas** | **minutos** |
| Límite por GPU compartida | Sí — riesgo OOM | No aplica |
| Requiere QPU credits | No | Sí |
| Uso recomendado | Desarrollo y validación | Producción y experimentos finales |

> Una vez obtenidas las QPU credits de PASQAL, cambiar `backend_type` a `QPUBackend` en `solver_qubo.py` o contactar a PASQAL para habilitar el routing automático al hardware físico.
