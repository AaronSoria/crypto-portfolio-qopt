package models

type Asset struct {
	Symbol     string `json:"symbol"`
	Provider   string `json:"provider"`
	VSCurrency string `json:"vs_currency"`
}
