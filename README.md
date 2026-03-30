# Crypto Portfolio QOpt

Scaffold para optimizacion de portafolios cripto con stack mixto:
- **Go** para ingesta de datos de mercado
- **Python** para modelado del problema, traduccion a formatos cuanticos, solvers, providers y benchmarking

## Vision de arquitectura

### 1. `data`
Responsable de traer, validar, limpiar y transformar datos crudos en un `PortfolioDataset` estandar.

### 2. `problem`
Define formulaciones abstractas de optimizacion de portafolio y las traduce a representaciones como QUBO, Ising, CQM o formatos nativos de backends.

### 3. `solvers`
Implementa algoritmos clasicos, cuanticos e hibridos desacoplados de la formulacion abstracta.

### 4. `providers`
Abstrae acceso a proveedores y simuladores con una interfaz basada en capacidades.

### 5. `benchmark`
Ejecuta experimentos comparables y guarda metricas reproducibles.

## Inicio rapido

### Python
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

### Go
```bash
go run ./cmd/ingest --provider coingecko --symbols BTC,ETH,SOL --vs-currency usd
```

### Experimento
```bash
python scripts/run_experiment.py --config configs/experiments/example_mean_variance.yaml
```


## Docker

### Build
```bash
docker compose build
```

### Run market data ingestion (Go)
```bash
docker compose run --rm ingest --provider coingecko --symbols BTC,ETH,SOL --vs-currency usd
```

### Run benchmark experiment (Python)
```bash
docker compose run --rm app
```

### Override experiment config
```bash
docker compose run --rm app python scripts/run_experiment.py --config configs/experiments/example_mean_variance.yaml
```
