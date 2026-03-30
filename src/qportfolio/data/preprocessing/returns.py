from qportfolio.data.schemas import PortfolioDataset


def compute_log_returns(dataset: PortfolioDataset) -> dict[str, list[float]]:
    return {asset.symbol: [] for asset in dataset.assets}
