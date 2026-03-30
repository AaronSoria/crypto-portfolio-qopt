package ingest

import "time"

type KrakenConnector struct{}

func NewKrakenConnector() *KrakenConnector { return &KrakenConnector{} }
func (c *KrakenConnector) Name() string    { return "kraken" }

func (c *KrakenConnector) FetchMarketData(cfg Config) ([]OHLCVRecord, error) {
    now := time.Now().UTC()
    records := make([]OHLCVRecord, 0, len(cfg.Symbols))
    for _, s := range cfg.Symbols {
        records = append(records, OHLCVRecord{Symbol: s, Timestamp: now})
    }
    return records, nil
}
