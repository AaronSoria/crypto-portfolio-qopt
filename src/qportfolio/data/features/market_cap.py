from qportfolio.data.schemas import PortfolioDataset


def estimate_market_caps(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: asset.market_cap or 0.0 for asset in dataset.assets}
