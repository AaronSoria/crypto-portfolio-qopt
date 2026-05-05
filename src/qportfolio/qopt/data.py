"""
Data models and loaders for crypto portfolio optimization.
Mirrors the Go PortfolioDataset schema.
"""
from __future__ import annotations

import json
import warnings
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
        """
        Load from a JSON file produced by the Go ingest pipeline.

        Handles two cases:
          - Multiple records per asset: uses log-return series for mu and Sigma
          - Single record per asset:   uses (high-low)/close as proxy volatility
            and close price rank as proxy expected return
        """
        with open(path) as f:
            raw = json.load(f)

        records = raw.get("records", [])
        symbols = [a["symbol"] for a in raw.get("assets", [])]
        if not records or not symbols:
            raise ValueError("JSON dataset has no records or assets")

        # Group closes by symbol
        closes: Dict[str, List[float]] = {s: [] for s in symbols}
        highs:  Dict[str, List[float]] = {s: [] for s in symbols}
        lows:   Dict[str, List[float]] = {s: [] for s in symbols}
        for r in records:
            s = r["symbol"]
            if s in closes:
                closes[s].append(r["close"])
                highs[s].append(r["high"])
                lows[s].append(r["low"])

        # Detect single-record-per-asset case
        max_records = max(len(v) for v in closes.values())

        if max_records >= 2:
            # Normal path: compute log-return series
            ret_series: Dict[str, np.ndarray] = {}
            for s, prices in closes.items():
                arr = np.array(prices)
                if len(arr) >= 2:
                    ret_series[s] = np.diff(np.log(arr))
                else:
                    ret_series[s] = np.array([0.0])

            exp_ret = {s: float(np.mean(v)) for s, v in ret_series.items()}
            mat = np.array([ret_series[s] for s in symbols])
            # np.cov needs at least 2 observations; pad if needed
            if mat.shape[1] < 2:
                mat = np.hstack([mat, mat])
            cov = np.cov(mat)

        else:
            # Fallback: single snapshot per asset
            # Use intraday range / close as volatility proxy
            # Use relative close rank as expected-return proxy
            warnings.warn(
                "Only 1 record per asset in JSON — using single-snapshot "
                "heuristics for mu and Sigma. Run ingest with --days 30+ "
                "for proper time-series estimates.",
                UserWarning,
                stacklevel=2,
            )
            n = len(symbols)
            close_vals = np.array([closes[s][0] for s in symbols], dtype=float)
            high_vals  = np.array([highs[s][0]  for s in symbols], dtype=float)
            low_vals   = np.array([lows[s][0]   for s in symbols], dtype=float)

            # Normalise closes to [0,1] range → proxy for relative return rank
            c_min, c_range = close_vals.min(), close_vals.max() - close_vals.min()
            if c_range > 0:
                mu_arr = (close_vals - c_min) / c_range * 0.20  # scale to ~0-20%
            else:
                mu_arr = np.full(n, 0.10)
            exp_ret = {s: float(mu_arr[i]) for i, s in enumerate(symbols)}

            # Intraday volatility proxy: (high - low) / close
            vol = (high_vals - low_vals) / np.where(close_vals > 0, close_vals, 1.0)
            # Build diagonal covariance with small off-diagonal correlation (0.1)
            cov = np.full((n, n), 0.1) * np.outer(vol, vol)
            np.fill_diagonal(cov, vol ** 2)

        return cls(symbols=symbols, expected_returns=exp_ret, covariance_matrix=cov)
