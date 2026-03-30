package storage

import (
	"encoding/json"
	"os"
	"path/filepath"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func SaveJSON(path string, dataset models.PortfolioDataset) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}

	file, err := os.Create(path)
	if err != nil {
		return err
	}
	defer file.Close()

	encoder := json.NewEncoder(file)
	encoder.SetIndent("", "  ")
	return encoder.Encode(dataset)
}
