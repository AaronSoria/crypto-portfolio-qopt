from qportfolio.data.schemas import PortfolioDataset


def estimate_transaction_cost(dataset: PortfolioDataset) -> dict[str, float]:
    return {asset.symbol: dataset.transaction_cost.get(asset.symbol, 0.0) for asset in dataset.assets}
