from qportfolio.data.schemas import PortfolioDataset


def estimate_liquidity(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: asset.liquidity_score or 0.0 for asset in dataset.assets}
