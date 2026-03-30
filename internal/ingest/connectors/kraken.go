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

type KrakenConnector struct{}

func NewKrakenConnector() *KrakenConnector { return &KrakenConnector{} }
func (c *KrakenConnector) Name() string    { return "kraken" }

type krakenResponse struct {
	Error  []string                   `json:"error"`
	Result map[string][][]interface{} `json:"result"`
}

type assetPair struct {
	AltName string `json:"altname"`
	WsName  string `json:"wsname"`
}

type assetPairsResponse struct {
	Error  []string             `json:"error"`
	Result map[string]assetPair `json:"result"`
}

func fetchKrakenPairs(client *http.Client) (map[string]string, error) {
	url := "https://api.kraken.com/0/public/AssetPairs"

	resp, err := client.Get(url)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	var data assetPairsResponse
	if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
		return nil, err
	}

	if len(data.Error) > 0 {
		return nil, fmt.Errorf("kraken error: %v", data.Error)
	}

	pairs := make(map[string]string)

	for _, p := range data.Result {
		// wsname: "XBT/USD"
		parts := strings.Split(p.WsName, "/")
		if len(parts) != 2 {
			continue
		}

		base := parts[0]
		quote := parts[1]

		key := base + quote // ej: XBTUSD
		pairs[key] = p.AltName
	}

	return pairs, nil
}

func normalizeBase(symbol string) string {
	switch strings.ToUpper(symbol) {
	case "BTC":
		return "XBT"
	default:
		return strings.ToUpper(symbol)
	}
}

func (c *KrakenConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	client := &http.Client{Timeout: 10 * time.Second}

	var records []models.OHLCVRecord

	since := time.Now().AddDate(0, 0, -cfg.Days).Unix()

	pairsMap, err := fetchKrakenPairs(client)
	if err != nil {
		return nil, err
	}

	for _, sym := range cfg.Symbols {

		base := normalizeBase(sym)
		quote := strings.ToUpper(cfg.VsCurrency)

		key := base + quote
		pair, ok := pairsMap[key]
		if !ok {
			continue // no existe en Kraken
		}

		url := fmt.Sprintf(
			"https://api.kraken.com/0/public/OHLC?pair=%s&since=%d",
			pair,
			since,
		)

		resp, err := client.Get(url)
		if err != nil {
			return nil, err
		}
		defer resp.Body.Close()

		if resp.StatusCode != http.StatusOK {
			return nil, fmt.Errorf("kraken error: %s", resp.Status)
		}

		var data krakenResponse
		if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
			return nil, err
		}

		if len(data.Error) > 0 {
			return nil, fmt.Errorf("kraken API error: %v", data.Error)
		}

		ohlcData, ok := data.Result[pair]
		if !ok || len(ohlcData) == 0 {
			continue
		}

		// 🔥 diferencia importante: ahora devolvemos TODAS las velas (no solo la última)
		for _, candle := range ohlcData {

			ts := int64(candle[0].(float64))
			open := parseFloat(candle[1])
			high := parseFloat(candle[2])
			low := parseFloat(candle[3])
			close := parseFloat(candle[4])
			volume := parseFloat(candle[6])

			record := models.OHLCVRecord{
				Symbol:    sym,
				Timestamp: time.Unix(ts, 0).UTC(),
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

func parseFloat(v interface{}) float64 {
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
