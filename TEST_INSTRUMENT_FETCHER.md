# Testing Instrument Fetcher

## Quick Start

### Option 1: Using Docker (Recommended)

If you're running the backend in Docker:

```bash
# Enter the backend container
docker-compose exec devagent-backend bash

# Run the test script
cd /app
python3 test_instrument.py --help
```

### Option 2: Install Dependencies Locally

```bash
# Install dependencies
cd app/backend
pip3 install -r requirements.txt

# Run the test script
python3 test_instrument.py --help
```

### Option 3: Using Python Interactive Shell

```bash
cd app/backend
python3

# Then in Python:
>>> import asyncio
>>> from tool_executor import find_instrument_by_segment, search_instruments
>>> from trading import trading_service

>>> # Test finding NIFTY
>>> result = asyncio.run(find_instrument_by_segment("IDX_I", "NIFTY"))
>>> print(result)

>>> # Test searching
>>> result = asyncio.run(search_instruments("NIFTY", instrument_type="INDEX"))
>>> print(result)
```

## Test Script Usage

The test script is located at: `app/backend/test_instrument.py`

### Examples:

```bash
# List all instruments from IDX_I segment
python3 test_instrument.py --list IDX_I

# Find NIFTY in IDX_I segment
python3 test_instrument.py --find IDX_I NIFTY

# Search for NIFTY across all segments
python3 test_instrument.py --search NIFTY

# Search for NIFTY in IDX_I with exact match
python3 test_instrument.py --search NIFTY --segment IDX_I --exact

# Search for RELIANCE in NSE_EQ
python3 test_instrument.py --find NSE_EQ RELIANCE

# List first 50 instruments from NSE_EQ
python3 test_instrument.py --list NSE_EQ --limit 50
```

## Available Commands

- `--list SEGMENT`: List all instruments from a segment (e.g., IDX_I, NSE_EQ)
- `--find SEGMENT SYMBOL`: Find a specific instrument by segment and symbol
- `--search QUERY`: Search for instruments across segments
- `--quote SYMBOL`: Find instrument and fetch market quote (price, OHLC, volume). Requires `--token` or `DHAN_ACCESS_TOKEN` env var
- `--token TOKEN`: DhanHQ access token (or set `DHAN_ACCESS_TOKEN` environment variable)
- `--segment SEGMENT`: Filter by exchange segment (use with --search)
- `--type TYPE`: Filter by instrument type: EQUITY, INDEX, FUTURES, OPTIONS (use with --search)
- `--exact`: Use exact match instead of substring match
- `--case-sensitive`: Case sensitive search
- `--limit N`: Limit number of results for list command (default: 20)

## Testing Specific Scenarios

### Test NIFTY Search
```bash
python3 test_instrument.py --search NIFTY --type INDEX
```

### Test RELIANCE Search
```bash
python3 test_instrument.py --search RELIANCE --type EQUITY
```

### List All Available Indices
```bash
python3 test_instrument.py --list IDX_I --limit 100
```

### Find with Exact Match
```bash
python3 test_instrument.py --find IDX_I "NIFTY 50" --exact
```

### Fetch Market Quote for NIFTY
```bash
# Using command line argument
python3 test_instrument_fetcher.py --quote NIFTY --token YOUR_ACCESS_TOKEN

# Using environment variable (recommended)
export DHAN_ACCESS_TOKEN=your_access_token_here
python3 test_instrument_fetcher.py --quote NIFTY

# Or set it in your shell profile (~/.bashrc, ~/.zshrc, etc.)
echo 'export DHAN_ACCESS_TOKEN=your_access_token_here' >> ~/.bashrc
source ~/.bashrc

# Fetch quote for other instruments
python3 test_instrument_fetcher.py --quote RELIANCE --token YOUR_ACCESS_TOKEN
python3 test_instrument_fetcher.py --quote "BANK NIFTY" --token YOUR_ACCESS_TOKEN
```

**Note:** The backend also supports `DHAN_ACCESS_TOKEN` as a fallback. If you set it in your environment, you can omit the `--token` parameter in API requests, and the backend will automatically use the environment variable.

**Note:** The `--quote` option will:
1. First search for the instrument by name
2. Extract the security_id and exchange_segment
3. Fetch the market quote (current price, open, high, low, close, volume)
4. Display formatted results with raw data for debugging

