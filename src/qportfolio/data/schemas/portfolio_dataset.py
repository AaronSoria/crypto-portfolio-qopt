from pydantic import BaseModel, Field

from .asset import Asset
from .market_snapshot import MarketSnapshot


class PortfolioDataset(BaseModel):
    assets: list[Asset]
    snapshots: list[MarketSnapshot]
    expected_returns: dict[str, float] = Field(default_factory=dict)
    covariance_matrix: dict[str, dict[str, float]] = Field(default_factory=dict)
    downside_risk: dict[str, float] = Field(default_factory=dict)
    transaction_cost: dict[str, float] = Field(default_factory=dict)
