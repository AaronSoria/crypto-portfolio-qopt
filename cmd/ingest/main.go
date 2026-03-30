package main

import (
	"flag"
	"fmt"
	"log"
	"strings"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest"
	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
)

func main() {
	provider := flag.String("provider", "coingecko", "data provider")
	symbols := flag.String("symbols", "BTC,ETH", "comma-separated symbols")
	vsCurrency := flag.String("vs-currency", "usd", "quote currency")
	interval := flag.String("interval", "daily", "data interval")
	out := flag.String("out", "data/raw/market_snapshot.json", "output dataset path")
	flag.Parse()

	cfg := config.Config{
		Provider:   *provider,
		Symbols:    splitSymbols(*symbols),
		VSCurrency: *vsCurrency,
		Interval:   *interval,
		OutputPath: *out,
	}

	dataset, err := ingest.Run(cfg)
	if err != nil {
		log.Fatal(err)
	}

	fmt.Printf(
		"ingested %d records for %d assets from %s into %s\n",
		len(dataset.Records),
		len(dataset.Assets),
		dataset.Provider,
		cfg.Normalized().OutputPath,
	)
}

func splitSymbols(raw string) []string {
	parts := strings.Split(raw, ",")
	out := make([]string, 0, len(parts))
	for _, p := range parts {
		s := strings.TrimSpace(p)
		if s != "" {
			out = append(out, s)
		}
	}
	return out
}
