from pydantic import BaseModel, Field


class MarketSnapshot(BaseModel):
    timestamp: str
    prices: dict[str, float]
    volumes: dict[str, float] = Field(default_factory=dict)
    market_caps: dict[str, float] = Field(default_factory=dict)
