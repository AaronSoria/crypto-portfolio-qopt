package pipeline

import (
	"sort"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

func ToPriceMatrix(dataset models.PortfolioDataset) models.PriceMatrix {

	// timestamps únicos
	tsMap := make(map[int64]struct{})
	for _, r := range dataset.Records {
		tsMap[r.Timestamp.Unix()] = struct{}{}
	}

	timestamps := make([]int64, 0, len(tsMap))
	for ts := range tsMap {
		timestamps = append(timestamps, ts)
	}

	sort.Slice(timestamps, func(i, j int) bool {
		return timestamps[i] < timestamps[j]
	})

	// índice de símbolos
	symbolIndex := make(map[string]int)
	for i, a := range dataset.Assets {
		symbolIndex[a.Symbol] = i
	}

	// matriz
	prices := make([][]float64, len(timestamps))
	for i := range prices {
		prices[i] = make([]float64, len(dataset.Assets))
	}

	// index timestamp
	tsIndex := make(map[int64]int)
	for i, ts := range timestamps {
		tsIndex[ts] = i
	}

	// llenar
	for _, r := range dataset.Records {
		t := tsIndex[r.Timestamp.Unix()]
		s := symbolIndex[r.Symbol]
		prices[t][s] = r.Close
	}

	return models.PriceMatrix{
		Symbols:    extractSymbols(dataset.Assets),
		Timestamps: timestamps,
		Prices:     prices,
	}
}

func extractSymbols(assets []models.Asset) []string {
	out := make([]string, len(assets))
	for i, a := range assets {
		out[i] = a.Symbol
	}
	return out
}
