package connectors

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

type CoinGeckoConnector struct{}

func NewCoinGeckoConnector() *CoinGeckoConnector { return &CoinGeckoConnector{} }
func (c *CoinGeckoConnector) Name() string       { return "coingecko" }

// --- CoinGecko response struct ---
type marketChartResponse struct {
	Prices       [][]float64 `json:"prices"`
	TotalVolumes [][]float64 `json:"total_volumes"`
}

type coinInfo struct {
	ID     string `json:"id"`
	Symbol string `json:"symbol"`
	Name   string `json:"name"`
}

func fetchCoinList(client *http.Client) (map[string]string, error) {
	url := "https://api.coingecko.com/api/v3/coins/list"

	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var coins []coinInfo
	if err := json.NewDecoder(resp.Body).Decode(&coins); err != nil {
		return nil, err
	}

	mapping := make(map[string]string)

	for _, c := range coins {
		symbol := strings.ToUpper(c.Symbol)

		// solo guardar si no existe (evita sobrescribir)
		if _, exists := mapping[symbol]; !exists {
			mapping[symbol] = c.ID
		}
	}

	return mapping, nil
}

func (c *CoinGeckoConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	client := &http.Client{Timeout: 10 * time.Second}

	var allRecords []models.OHLCVRecord

	symbolMap, err := fetchCoinList(client)

	if err != nil {
		return nil, err
	}

	for _, sym := range cfg.Symbols {

		coinID, ok := symbolMap[strings.ToUpper(sym)]
		if !ok {
			continue // o error, según diseño
		}

		url := fmt.Sprintf(
			"https://api.coingecko.com/api/v3/coins/%s/market_chart?vs_currency=%s&days=1",
			coinID,
			cfg.VsCurrency,
		)

		resp, err := client.Get(url)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("coingecko error: %s", resp.Status)
		}

		var data marketChartResponse
		if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
			return nil, err
		}

		if len(data.Prices) == 0 {
			continue
		}

		// --- construir OHLC ---
		open := data.Prices[0][1]
		close := data.Prices[len(data.Prices)-1][1]

		high := open
		low := open

		for _, p := range data.Prices {
			price := p[1]
			if price > high {
				high = price
			}
			if price < low {
				low = price
			}
		}

		// volumen (último disponible)
		var volume float64
		if len(data.TotalVolumes) > 0 {
			volume = data.TotalVolumes[len(data.TotalVolumes)-1][1]
		}

		// timestamp → último punto
		lastTs := int64(data.Prices[len(data.Prices)-1][0])
		timestamp := time.UnixMilli(lastTs).UTC()

		record := models.OHLCVRecord{
			Symbol:    sym,
			Timestamp: timestamp,
			Open:      open,
			High:      high,
			Low:       low,
			Close:     close,
			Volume:    volume,
		}

		allRecords = append(allRecords, record)
	}

	return allRecords, nil
}
