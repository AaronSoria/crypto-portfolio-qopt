"""
Data models and loaders for crypto portfolio optimization.
Mirrors the Go PortfolioDataset schema.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np


@dataclass
class PortfolioDataset:
    """Standardised in-memory representation of market data."""
    symbols: List[str]
    expected_returns: Dict[str, float]        # mu_i
    covariance_matrix: np.ndarray             # Sigma  (n x n)
    symbol_index: Dict[str, int] = field(init=False)

    def __post_init__(self):
        self.symbol_index = {s: i for i, s in enumerate(self.symbols)}

    @property
    def n(self) -> int:
        return len(self.symbols)

    @property
    def mu(self) -> np.ndarray:
        return np.array([self.expected_returns[s] for s in self.symbols])

    @classmethod
    def from_config(cls, cfg: dict) -> "PortfolioDataset":
        """Build dataset from experiment YAML config (in-memory source)."""
        symbols = list(cfg["expected_returns"].keys())
        exp_ret = cfg["expected_returns"]
        cov_raw = cfg["covariance_matrix"]
        n = len(symbols)
        cov = np.zeros((n, n))
        for i, si in enumerate(symbols):
            for j, sj in enumerate(symbols):
                cov[i, j] = cov_raw[si][sj]
        return cls(symbols=symbols, expected_returns=exp_ret, covariance_matrix=cov)

    @classmethod
    def from_json(cls, path: str | Path) -> "PortfolioDataset":
        """Load from a JSON file produced by the Go ingest pipeline."""
        with open(path) as f:
            raw = json.load(f)
        # Compute returns and covariance from OHLCV records
        records = raw.get("records", [])
        symbols = [a["symbol"] for a in raw.get("assets", [])]
        if not records or not symbols:
            raise ValueError("JSON dataset has no records or assets")

        closes: Dict[str, List[float]] = {s: [] for s in symbols}
        for r in records:
            s = r["symbol"]
            if s in closes:
                closes[s].append(r["close"])

        ret_series = {}
        for s, prices in closes.items():
            arr = np.array(prices)
            if len(arr) > 1:
                ret_series[s] = np.diff(np.log(arr))

        exp_ret = {s: float(np.mean(v)) for s, v in ret_series.items()}
        mat = np.array([ret_series[s] for s in symbols])
        cov = np.cov(mat)
        return cls(symbols=symbols, expected_returns=exp_ret, covariance_matrix=cov)
