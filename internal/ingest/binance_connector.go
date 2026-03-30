package ingest

import "time"

type BinanceConnector struct{}

func NewBinanceConnector() *BinanceConnector { return &BinanceConnector{} }
func (c *BinanceConnector) Name() string     { return "binance" }

func (c *BinanceConnector) FetchMarketData(cfg Config) ([]OHLCVRecord, error) {
    now := time.Now().UTC()
    records := make([]OHLCVRecord, 0, len(cfg.Symbols))
    for _, s := range cfg.Symbols {
        records = append(records, OHLCVRecord{Symbol: s, Timestamp: now})
    }
    return records, nil
}
