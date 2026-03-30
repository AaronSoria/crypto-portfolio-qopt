package main

import (
    "flag"
    "fmt"
    "log"
    "strings"

    "github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest"
)

func main() {
    provider := flag.String("provider", "coingecko", "data provider")
    symbols := flag.String("symbols", "BTC,ETH", "comma-separated symbols")
    vsCurrency := flag.String("vs-currency", "usd", "quote currency")
    interval := flag.String("interval", "daily", "data interval")
    flag.Parse()

    cfg := ingest.Config{
        Provider:   *provider,
        Symbols:    splitSymbols(*symbols),
        VSCurrency: *vsCurrency,
        Interval:   *interval,
    }

    records, err := ingest.Run(cfg)
    if err != nil {
        log.Fatal(err)
    }

    fmt.Printf("ingested %d records from %s\n", len(records), cfg.Provider)
}

func splitSymbols(raw string) []string {
    parts := strings.Split(raw, ",")
    out := make([]string, 0, len(parts))
    for _, p := range parts {
        s := strings.TrimSpace(p)
        if s != "" {
            out = append(out, strings.ToUpper(s))
        }
    }
    return out
}
