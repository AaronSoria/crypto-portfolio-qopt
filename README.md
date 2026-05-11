# Crypto Portfolio QOpt

Quantum portfolio optimisation for crypto assets using Pasqal neutral-atom hardware.

Ingests real market data from CoinGecko (Go), formulates a Markowitz mean-variance QUBO, and solves it with a Rydberg atom pulse sequence on Pasqal Cloud — with automatic fallback to local simulation.

---

## Architecture

```
ingest (Go)          data.py              problem.py           solver_pasqal.py
CoinGecko API   →   PortfolioDataset  →  QUBO n×n         →  Rydberg pulse sequence
market_snapshot      mu, Sigma            Markowitz              Pasqal Cloud EMU_FREE
     .json           covariance           penalty budget         or numpy_rydberg
                                                                 or sa_hybrid
                                              ↓
                                         benchmark.py  →  results/logs/*.json
                                         exact / greedy / Pasqal comparison
```

**Backend routing** (automatic by problem size):

| n assets | Backend | Requirement |
|----------|---------|-------------|
| ≤ 20 | `numpy_rydberg` | none — always available |
| ≤ 100 | `pulser_local` | `pip install pulser pulser-simulation` |
| ≤ 100 | `pulser_cloud` | Pasqal Cloud account + `.env.pasqal` |
| any n | `sa_hybrid` | none — scipy fallback |

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

## Scaling to n assets

Three experiment configs are included:

| Config | Assets | Backend |
|--------|--------|---------|
| `pasqal_mean_variance.yaml` | 3 (BTC, ETH, SOL) — real market data | `pulser_cloud` / `numpy_rydberg` |
| `pasqal_n10.yaml` | 10 assets — in-memory | `pulser_cloud` / `sa_hybrid` |
| `pasqal_n25.yaml` | 25 assets — JSON data | `pulser_cloud` / `sa_hybrid` |

Run any config:

```bash
docker compose run --rm ingest   # fetch fresh market data first (for json source)

docker compose run --rm app python scripts/run_experiment.py \
  --config configs/experiments/pasqal_n10.yaml \
  --persist \
  --output-dir results/logs
```

To add your own assets, edit the `symbols` in `docker-compose.yml` (ingest service) and the `expected_returns` / `covariance_matrix` in your experiment YAML.

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
│   ├── solver_pasqal.py   Rydberg solver (numpy / pulser_local / pulser_cloud / SA)
│   ├── solver_classical.py Greedy + exact brute-force (reference)
│   ├── benchmark.py       Pipeline: data → QUBO → solve → report
│   └── credentials.py     Loads .env.pasqal with priority chain
├── scripts/
│   └── run_experiment.py  CLI entrypoint
├── configs/experiments/   YAML experiment configs
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

## Hardware limits (Pasqal Fresnel QPU)

| Parameter | Value |
|-----------|-------|
| Max atoms | 80 |
| Max Ω (Rabi frequency) | 12.566 rad/μs (2π × 2 MHz) |
| Max \|δ\| (detuning) | 125.66 rad/μs |
| Max sequence duration | 6000 ns |
| C₆ coefficient (Rb87) | 862,690 rad·μs⁻¹·μm⁶ |

The solver automatically stays within these limits. For n > 20 without Pasqal Cloud credentials, it falls back to `sa_hybrid` (scipy dual annealing).
