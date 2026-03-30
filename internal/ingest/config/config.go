package config

import "strings"

type Config struct {
	Provider   string
	Symbols    []string
	VsCurrency string
	Days       int
	OutputPath string
}

func (c Config) Normalized() Config {
	out := c
	out.Provider = strings.ToLower(strings.TrimSpace(out.Provider))
	out.VsCurrency = strings.ToLower(strings.TrimSpace(out.VsCurrency))
	cleaned := make([]string, 0, len(out.Symbols))
	for _, s := range out.Symbols {
		s = strings.ToUpper(strings.TrimSpace(s))
		if s != "" {
			cleaned = append(cleaned, s)
		}
	}
	out.Symbols = cleaned
	if out.Days == 0 {
		out.Days = 30
	}
	if out.OutputPath == "" {
		out.OutputPath = "data/raw/market_snapshot.json"
	}
	return out
}
