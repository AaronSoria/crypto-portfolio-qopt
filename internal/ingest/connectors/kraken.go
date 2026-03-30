package connectors

import (
	"time"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

type KrakenConnector struct{}

func NewKrakenConnector() *KrakenConnector { return &KrakenConnector{} }
func (c *KrakenConnector) Name() string    { return "kraken" }

func (c *KrakenConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	now := time.Now().UTC()
	records := make([]models.OHLCVRecord, 0, len(cfg.Symbols))
	for _, s := range cfg.Symbols {
		records = append(records, models.OHLCVRecord{Symbol: s, Timestamp: now})
	}
	return records, nil
}
