FROM golang:1.22-alpine AS builder

WORKDIR /src
COPY go.mod ./
COPY cmd ./cmd
COPY internal ./internal

RUN go build -o /out/ingest ./cmd/ingest

FROM alpine:3.20
WORKDIR /app
COPY --from=builder /out/ingest /usr/local/bin/ingest

ENTRYPOINT ["ingest"]
CMD ["--provider", "coingecko", "--symbols", "BTC,ETH,SOL", "--vs-currency", "usd"]
