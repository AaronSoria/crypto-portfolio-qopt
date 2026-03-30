from qportfolio.data.schemas import PortfolioDataset


def covariance_matrix(dataset: PortfolioDataset) -> dict[str, dict[str, float]]:
    return {asset.symbol: {} for asset in dataset.assets}


def volatility(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: 0.0 for asset in dataset.assets}


def correlations(dataset: PortfolioDataset) -> dict[str, dict[str, float]]:
    return {asset.symbol: {} for asset in dataset.assets}
