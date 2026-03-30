package storage

import (
	"fmt"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func SaveParquet(path string, dataset models.PortfolioDataset) error {
	return fmt.Errorf("parquet not implemented yet")
}
