from pydantic import BaseModel


class Asset(BaseModel):
    symbol: str
    name: str | None = None
    market_cap: float | None = None
    liquidity_score: float | None = None
