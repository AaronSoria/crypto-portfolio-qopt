package connectors

import (
	"encoding/json"
	"fmt"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/models"
)

type BinanceConnector struct{}

func NewBinanceConnector() *BinanceConnector { return &BinanceConnector{} }
func (c *BinanceConnector) Name() string     { return "binance" }

// --- normalizar quote ---
func normalizeQuote(q string) string {
	switch strings.ToUpper(q) {
	case "USD":
		return "USDT"
	default:
		return strings.ToUpper(q)
	}
}

// --- respuesta ---
type binanceKline []interface{}

func (c *BinanceConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	client := &http.Client{Timeout: 10 * time.Second}

	var records []models.OHLCVRecord

	quote := normalizeQuote(cfg.VsCurrency)
	limit := cfg.Days // usamos días como número de velas (1 vela = 1 día)

	for _, sym := range cfg.Symbols {

		symbol := strings.ToUpper(sym) + quote

		url := fmt.Sprintf(
			"https://api.binance.com/api/v3/klines?symbol=%s&interval=1d&limit=%d",
			symbol,
			limit,
		)

		resp, err := client.Get(url)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("binance error: %s", resp.Status)
		}

		var data []binanceKline
		if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
			return nil, err
		}

		if len(data) == 0 {
			continue
		}

		for _, k := range data {

			ts := int64(k[0].(float64))
			open := parseStrFloat(k[1])
			high := parseStrFloat(k[2])
			low := parseStrFloat(k[3])
			close := parseStrFloat(k[4])
			volume := parseStrFloat(k[5])

			record := models.OHLCVRecord{
				Symbol:    sym,
				Timestamp: time.UnixMilli(ts).UTC(),
				Open:      open,
				High:      high,
				Low:       low,
				Close:     close,
				Volume:    volume,
			}

			records = append(records, record)
		}
	}

	return records, nil
}

// helper
func parseStrFloat(v interface{}) float64 {
	switch val := v.(type) {
	case string:
		f, _ := strconv.ParseFloat(val, 64)
		return f
	case float64:
		return val
	default:
		return 0
	}
}
