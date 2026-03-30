package pipeline

import (
	"strings"

	"github.com/aaroon2895/crypto-portfolio-qopt/internal/ingest/config"
)

func NormalizeConfig(cfg config.Config) config.Config {
	normalized := cfg

	normalized.Provider = strings.ToLower(cfg.Provider)
	normalized.VsCurrency = strings.ToLower(cfg.VsCurrency)

	for i, s := range cfg.Symbols {
		normalized.Symbols[i] = strings.ToLower(strings.TrimSpace(s))
	}

	return normalized
}
