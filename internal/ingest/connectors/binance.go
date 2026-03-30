package connectors

import (
	"time"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

type BinanceConnector struct{}

func NewBinanceConnector() *BinanceConnector { return &BinanceConnector{} }
func (c *BinanceConnector) Name() string     { return "binance" }

func (c *BinanceConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	now := time.Now().UTC()
	records := make([]models.OHLCVRecord, 0, len(cfg.Symbols))
	for _, s := range cfg.Symbols {
		records = append(records, models.OHLCVRecord{Symbol: s, Timestamp: now})
	}
	return records, nil
}
