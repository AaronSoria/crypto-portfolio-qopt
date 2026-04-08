from __future__ import annotations
from typing import Dict

def liquidity_score(dataset) -> Dict[str, float]:
    """Average normalized volume as liquidity proxy."""
    symbols = [a.symbol.upper() for a in dataset.assets]
    volumes = {s: [] for s in symbols}

    for snap in dataset.snapshots:
        for s in symbols:
            v = snap.volumes.get(s)
            if v is not None:
                volumes[s].append(v)

    avg = {s: (sum(v)/len(v) if len(v)>0 else 0.0) for s,v in volumes.items()}
    max_v = max(avg.values()) if len(avg)>0 else 1.0

    if max_v == 0:
        return {s: 0.0 for s in symbols}

    return {s: avg[s]/max_v for s in symbols}
