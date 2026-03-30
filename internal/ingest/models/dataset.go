package models

type PortfolioDataset struct {
	Provider   string        `json:"provider"`
	VsCurrency string        `json:"vs_currency"`
	Days       int           `json:"days"`
	Assets     []Asset       `json:"assets"`
	Records    []OHLCVRecord `json:"records"`
}
