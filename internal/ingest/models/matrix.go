package models

type PriceMatrix struct {
	Symbols    []string
	Timestamps []int64
	Prices     [][]float64 // [t][asset]
}
