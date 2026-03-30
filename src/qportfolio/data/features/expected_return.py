from qportfolio.data.schemas import PortfolioDataset


def estimate_expected_return(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: dataset.expected_returns.get(asset.symbol, 0.0) for asset in dataset.assets}
