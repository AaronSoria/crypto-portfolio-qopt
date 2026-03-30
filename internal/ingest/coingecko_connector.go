package ingest

import "time"

type CoinGeckoConnector struct{}

func NewCoinGeckoConnector() *CoinGeckoConnector { return &CoinGeckoConnector{} }
func (c *CoinGeckoConnector) Name() string       { return "coingecko" }

func (c *CoinGeckoConnector) FetchMarketData(cfg Config) ([]OHLCVRecord, error) {
    now := time.Now().UTC()
    records := make([]OHLCVRecord, 0, len(cfg.Symbols))
    for _, s := range cfg.Symbols {
        records = append(records, OHLCVRecord{Symbol: s, Timestamp: now})
    }
    return records, nil
}
