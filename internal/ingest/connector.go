package ingest

type Connector interface {
    FetchMarketData(cfg Config) ([]OHLCVRecord, error)
    Name() string
}
