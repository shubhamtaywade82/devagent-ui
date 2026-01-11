## Canonical examples (for agent reasoning)

These examples are **documentation only**. Do **not** hardcode these values into logic.

### NIFTY (Index)

Instrument context:

```json
{
  "symbol": "NIFTY",
  "security_id": "13",
  "exchange_segment": "IDX_I",
  "instrument_type": "INDEX"
}
```

Intraday 5-min (same day):

```json
{
  "security_id": "13",
  "exchange_segment": "IDX_I",
  "instrument_type": "INDEX",
  "interval": "5",
  "from_date": "2026-01-11",
  "to_date": "2026-01-11"
}
```

### SENSEX (Index)

```json
{
  "security_id": "51",
  "exchange_segment": "IDX_I",
  "instrument_type": "INDEX"
}
```

### RELIANCE (Equity)

```json
{
  "security_id": "2885",
  "exchange_segment": "NSE_EQ",
  "instrument_type": "EQUITY"
}
```

Daily OHLCV (last ~3 months):

```json
{
  "security_id": "2885",
  "exchange_segment": "NSE_EQ",
  "instrument_type": "EQUITY",
  "from_date": "2025-10-01",
  "to_date": "2026-01-11"
}
```

### Options workflow (high-level)

- Resolve underlying (symbol -> `security_id`, `exchange_segment`)
- Fetch expiries (if needed)
- Fetch option chain (`underlying_security_id`, `exchange_segment`, `expiry_date`)
- Select a specific option contract (`security_id`, `exchange_segment`, `option_type`, `strike_price`, `expiry_date`)

