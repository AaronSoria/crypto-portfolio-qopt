package connectors

import (
	"fmt"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

type RawPricePoint struct {
	TimestampMs int64 // viene del API
	Price       float64
	Volume      float64
}

type MarketData struct {
	Symbol string
	Points []RawPricePoint
}

type Connector interface {
	FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error)
	Name() string
}

func GetConnector(name string) Connector {
	switch name {
	case "coingecko":
		return &CoinGeckoConnector{}
	case "binance":
		return &BinanceConnector{}
	case "kraken":
		return &KrakenConnector{}
	default:
		panic(fmt.Sprintf("unknown provider: %s", name))
	}
}
