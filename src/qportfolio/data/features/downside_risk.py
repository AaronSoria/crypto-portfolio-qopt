from qportfolio.data.schemas import PortfolioDataset


def estimate_downside_risk(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: dataset.downside_risk.get(asset.symbol, 0.0) for asset in dataset.assets}
