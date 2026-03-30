package pipeline

import "github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"

func RecordCountBySymbol(records []models.OHLCVRecord) map[string]int {
	counts := make(map[string]int, len(records))
	for _, record := range records {
		counts[record.Symbol]++
	}
	return counts
}
