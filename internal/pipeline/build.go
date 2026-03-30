package pipeline

import (
	"sort"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func BuildDataset(
	cfg config.Config,
	providerName string,
	records []models.OHLCVRecord,
) models.PortfolioDataset {
	normalized := append([]models.OHLCVRecord(nil), records...)

	sort.Slice(normalized, func(i, j int) bool {
		if normalized[i].Timestamp.Equal(normalized[j].Timestamp) {
			return normalized[i].Symbol < normalized[j].Symbol
		}
		return normalized[i].Timestamp.Before(normalized[j].Timestamp)
	})

	assets := make([]models.Asset, 0, len(cfg.Symbols))
	for _, symbol := range cfg.Symbols {
		assets = append(assets, models.Asset{
			Symbol:     symbol,
			Provider:   providerName,
			VSCurrency: cfg.VsCurrency,
		})
	}

	return models.PortfolioDataset{
		Provider:   providerName,
		VsCurrency: cfg.VsCurrency,
		Days:       cfg.Days,
		Assets:     assets,
		Records:    normalized,
	}
}
