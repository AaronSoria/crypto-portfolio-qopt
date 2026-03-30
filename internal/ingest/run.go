package ingest

import "fmt"

func Run(cfg Config) ([]OHLCVRecord, error) {
    var connector Connector
    switch cfg.Provider {
    case "binance":
        connector = NewBinanceConnector()
    case "kraken":
        connector = NewKrakenConnector()
    case "coingecko":
        connector = NewCoinGeckoConnector()
    default:
        return nil, fmt.Errorf("unsupported provider: %s", cfg.Provider)
    }
    return connector.FetchMarketData(cfg)
}
