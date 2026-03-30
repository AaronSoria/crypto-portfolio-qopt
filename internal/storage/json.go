package storage

import (
	"encoding/json"
	"os"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func SaveJSON(path string, dataset models.PortfolioDataset) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	encoder := json.NewEncoder(f)
	encoder.SetIndent("", "  ")

	return encoder.Encode(dataset)
}
