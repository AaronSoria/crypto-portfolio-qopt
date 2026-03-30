package pipeline

import (
	"context"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/connectors"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func FetchRecords(ctx context.Context, cfg config.Config) (connectors.Connector, []models.OHLCVRecord, error) {
	conn := connectors.GetConnector(cfg.Provider)

	records, err := conn.FetchMarketData(cfg)
	if err != nil {
		return conn, nil, err
	}

	return conn, records, nil
}
