package ingest

import (
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/pipeline"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/storage"
)

func Run(cfg config.Config) (models.PortfolioDataset, error) {
	normalizedCfg := pipeline.NormalizeConfig(cfg)

	connector, records, err := pipeline.FetchRecords(normalizedCfg)
	if err != nil {
		return models.PortfolioDataset{}, err
	}

	dataset := pipeline.BuildDataset(normalizedCfg, connector.Name(), records)

	if err := storage.SaveJSON(normalizedCfg.OutputPath, dataset); err != nil {
		return models.PortfolioDataset{}, err
	}

	return dataset, nil
}
