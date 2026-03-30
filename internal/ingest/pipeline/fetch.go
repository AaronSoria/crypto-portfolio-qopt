package pipeline

import (
	"fmt"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/connectors"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func ResolveConnector(provider string) (connectors.Connector, error) {
	switch provider {
	case "binance":
		return connectors.NewBinanceConnector(), nil
	case "kraken":
		return connectors.NewKrakenConnector(), nil
	case "coingecko":
		return connectors.NewCoinGeckoConnector(), nil
	default:
		return nil, fmt.Errorf("unsupported provider: %s", provider)
	}
}

func FetchRecords(cfg config.Config) (connectors.Connector, []models.OHLCVRecord, error) {
	conn := connectors.GetConnector(cfg.Provider)

	records, err := conn.FetchMarketData(cfg)
	if err != nil {
		return conn, nil, err
	}

	return conn, records, nil
}
