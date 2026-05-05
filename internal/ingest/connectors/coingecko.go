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

type coinInfo struct {
	ID     string `json:"id"`
	Symbol string `json:"symbol"`
}

type ohlcResponse [][]float64

type marketChartResponse struct {
	TotalVolumes [][]float64 `json:"total_volumes"`
}

// getWithRetry performs a GET with exponential backoff on 429.
// Retries up to maxRetries times, doubling wait each time.
func getWithRetry(client *http.Client, url string, maxRetries int) (*http.Response, error) {
	wait := 15 * time.Second
	for attempt := 0; attempt <= maxRetries; attempt++ {
		resp, err := client.Get(url)
		if err != nil {
			return nil, err
		}
		if resp.StatusCode == http.StatusTooManyRequests {
			resp.Body.Close()
			if attempt == maxRetries {
				return nil, fmt.Errorf("rate limited after %d retries: %s", maxRetries, url)
			}
			fmt.Printf("  [coingecko] rate limited, waiting %s before retry %d/%d...\n",
				wait, attempt+1, maxRetries)
			time.Sleep(wait)
			wait *= 2
			continue
		}
		return resp, nil
	}
	return nil, fmt.Errorf("unreachable")
}

func fetchCoinList(client *http.Client) (map[string]string, error) {
	resp, err := getWithRetry(client, "https://api.coingecko.com/api/v3/coins/list", 3)
	if err != nil {
		return nil, fmt.Errorf("fetchCoinList: %w", err)
	}
	defer resp.Body.Close()

	var coins []coinInfo
	if err := json.NewDecoder(resp.Body).Decode(&coins); err != nil {
		return nil, err
	}
	mapping := make(map[string]string)
	for _, c := range coins {
		sym := strings.ToUpper(c.Symbol)
		if _, exists := mapping[sym]; !exists {
			mapping[sym] = c.ID
		}
	}
	return mapping, nil
}

func ohlcDaysParam(days int) int {
	allowed := []int{1, 7, 14, 30, 90, 180, 365}
	best := allowed[0]
	for _, v := range allowed {
		if v <= days {
			best = v
		}
	}
	if days > 365 {
		best = 365
	}
	return best
}

func (c *CoinGeckoConnector) FetchMarketData(cfg config.Config) ([]models.OHLCVRecord, error) {
	client := &http.Client{Timeout: 20 * time.Second}

	fmt.Println("  [coingecko] fetching coin list...")
	symbolMap, err := fetchCoinList(client)
	if err != nil {
		return nil, err
	}
	// Pause after coin list to avoid immediate rate limit
	time.Sleep(6 * time.Second)

	days := ohlcDaysParam(cfg.Days)
	var allRecords []models.OHLCVRecord

	for i, sym := range cfg.Symbols {
		coinID, ok := symbolMap[strings.ToUpper(sym)]
		if !ok {
			return nil, fmt.Errorf("symbol not found in CoinGecko: %s", sym)
		}
		fmt.Printf("  [coingecko] fetching %s (id=%s, days=%d) [%d/%d]\n",
			sym, coinID, days, i+1, len(cfg.Symbols))

		// --- OHLC candles ---
		ohlcURL := fmt.Sprintf(
			"https://api.coingecko.com/api/v3/coins/%s/ohlc?vs_currency=%s&days=%d",
			coinID, cfg.VsCurrency, days,
		)
		ohlcResp, err := getWithRetry(client, ohlcURL, 4)
		if err != nil {
			return nil, fmt.Errorf("ohlc %s: %w", sym, err)
		}
		if ohlcResp.StatusCode != http.StatusOK {
			ohlcResp.Body.Close()
			return nil, fmt.Errorf("ohlc error %s: %s", sym, ohlcResp.Status)
		}
		var ohlc ohlcResponse
		if err := json.NewDecoder(ohlcResp.Body).Decode(&ohlc); err != nil {
			ohlcResp.Body.Close()
			return nil, fmt.Errorf("ohlc decode %s: %w", sym, err)
		}
		ohlcResp.Body.Close()

		if len(ohlc) == 0 {
			return nil, fmt.Errorf("no OHLC data for %s", sym)
		}
		fmt.Printf("  [coingecko] got %d candles for %s\n", len(ohlc), sym)

		// Pause between the two calls for the same symbol
		time.Sleep(6 * time.Second)

		// --- Volumes via market_chart ---
		volURL := fmt.Sprintf(
			"https://api.coingecko.com/api/v3/coins/%s/market_chart?vs_currency=%s&days=%d&interval=daily",
			coinID, cfg.VsCurrency, days,
		)
		volResp, err := getWithRetry(client, volURL, 4)
		if err != nil {
			return nil, fmt.Errorf("volume %s: %w", sym, err)
		}
		if volResp.StatusCode != http.StatusOK {
			volResp.Body.Close()
			return nil, fmt.Errorf("volume error %s: %s", sym, volResp.Status)
		}
		var chart marketChartResponse
		if err := json.NewDecoder(volResp.Body).Decode(&chart); err != nil {
			volResp.Body.Close()
			return nil, fmt.Errorf("volume decode %s: %w", sym, err)
		}
		volResp.Body.Close()

		// ts→volume lookup keyed by day bucket
		volByDay := make(map[int64]float64)
		for _, v := range chart.TotalVolumes {
			if len(v) < 2 {
				continue
			}
			volByDay[int64(v[0])/86400000] = v[1]
		}

		// Convert candles to OHLCVRecord
		for _, candle := range ohlc {
			if len(candle) < 5 {
				continue
			}
			tsMs := int64(candle[0])
			record := models.OHLCVRecord{
				Symbol:    sym,
				Timestamp: time.UnixMilli(tsMs).UTC(),
				Open:      candle[1],
				High:      candle[2],
				Low:       candle[3],
				Close:     candle[4],
				Volume:    volByDay[tsMs/86400000],
			}
			allRecords = append(allRecords, record)
		}

		// Pause between symbols
		if i < len(cfg.Symbols)-1 {
			fmt.Printf("  [coingecko] pausing 8s before next symbol...\n")
			time.Sleep(8 * time.Second)
		}
	}

	return allRecords, nil
}
