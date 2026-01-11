# DhanHQ Historical Data Implementation

## Overview

Implemented historical intraday data functionality following the official DhanHQ-py examples. The implementation supports both daily and intraday minute data retrieval.

## Official Example Pattern

From `examples/historical_data.py`:

```python
from dhanhq import DhanContext, dhanhq

# 1. Initialize Context
client_id = "YOUR_CLIENT_ID"
access_token = "YOUR_ACCESS_TOKEN"
dhan_context = DhanContext(client_id, access_token)
dhan = dhanhq(dhan_context)

# 2. Fetch Daily Historical Data
daily_data = dhan.historical_daily_data(
    security_id="1333",  # String format
    exchange_segment=dhan.NSE,  # Use constant
    instrument_type="EQUITY",
    from_date="2023-01-01",
    to_date="2023-01-31"
)

# 3. Fetch Intraday Minute Data
intraday_data = dhan.intraday_minute_data(
    security_id="1333",  # String format
    exchange_segment=dhan.NSE,  # Use constant
    instrument_type="EQUITY",
    from_date="2023-01-30",
    to_date="2023-01-31"
)
```

## Implementation Updates

### 1. Backend: `trading.py` - `get_historical_data()` Method

**Key Changes:**
- ✅ Uses `DhanContext` when available (with fallback to tuple for compatibility)
- ✅ Converts `security_id` to string (per official example: `"1333"` not `1333`)
- ✅ Maps exchange segment strings to `dhan.NSE`, `dhan.BSE` constants when available
- ✅ Supports both daily and intraday minute data
- ✅ Proper error handling and documentation

**Method Signature:**
```python
def get_historical_data(
    self,
    access_token: str,
    security_id: int,
    exchange_segment: str,
    instrument_type: str,
    from_date: str,  # Format: "YYYY-MM-DD"
    to_date: str,     # Format: "YYYY-MM-DD"
    interval: str = "daily"  # "daily" | "intraday" | "minute"
) -> Dict[str, Any]
```

**Interval Options:**
- `"daily"` or `"day"` → Calls `dhan.historical_daily_data()`
- `"intraday"`, `"minute"`, or `"intraday_minute"` → Calls `dhan.intraday_minute_data()`

### 2. Backend: `main.py` - API Endpoint

**Endpoint:** `POST /api/trading/market/historical`

**Request Model:**
```python
class HistoricalDataRequest(BaseModel):
    access_token: str
    security_id: Union[int, str]  # Accepts both formats
    exchange_segment: str
    instrument_type: str
    from_date: str  # Format: "YYYY-MM-DD"
    to_date: str    # Format: "YYYY-MM-DD"
    interval: str = "daily"  # "daily" | "intraday" | "minute"
```

**Example Request:**
```json
{
    "access_token": "your_access_token",
    "security_id": "1333",  // or 1333 (both accepted)
    "exchange_segment": "NSE_EQ",
    "instrument_type": "EQUITY",
    "from_date": "2023-01-01",
    "to_date": "2023-01-31",
    "interval": "daily"  // or "intraday" for minute data
}
```

**Response:**
```json
{
    "success": true,
    "data": {
        // Historical data array with OHLC, volume, etc.
    }
}
```

## Features

### Daily Historical Data
- Retrieves daily OHLC (Open, High, Low, Close) data
- Volume and other daily metrics
- Date range support

### Intraday Minute Data
- Retrieves minute-by-minute OHLC data
- High-frequency intraday data
- Useful for technical analysis and charting

## Usage Examples

### Python Client
```python
import requests

# Daily data
response = requests.post("http://localhost:8000/api/trading/market/historical", json={
    "access_token": "your_token",
    "security_id": "1333",
    "exchange_segment": "NSE_EQ",
    "instrument_type": "EQUITY",
    "from_date": "2023-01-01",
    "to_date": "2023-01-31",
    "interval": "daily"
})

# Intraday minute data
response = requests.post("http://localhost:8000/api/trading/market/historical", json={
    "access_token": "your_token",
    "security_id": "1333",
    "exchange_segment": "NSE_EQ",
    "instrument_type": "EQUITY",
    "from_date": "2023-01-30",
    "to_date": "2023-01-31",
    "interval": "intraday"
})
```

### JavaScript/Frontend
```javascript
// Using the API service
const data = await api.getHistoricalData({
    access_token: token,
    security_id: "1333",
    exchange_segment: "NSE_EQ",
    instrument_type: "EQUITY",
    from_date: "2023-01-01",
    to_date: "2023-01-31",
    interval: "daily"  // or "intraday"
});
```

## Differences from Previous Implementation

### Before:
- Used tuple `(client_id, access_token)` instead of `DhanContext`
- Security ID was passed as integer
- No exchange constant mapping
- Basic error handling

### After:
- ✅ Uses `DhanContext` when available (per official example)
- ✅ Converts security_id to string (per official example)
- ✅ Maps exchange segments to constants (`dhan.NSE`, etc.) when available
- ✅ Enhanced error handling and documentation
- ✅ Supports both daily and intraday intervals
- ✅ Better parameter validation

## Exchange Segment Mapping

The implementation automatically maps exchange segment strings to DhanHQ constants:

| Exchange Segment String | Constant Used |
|-------------------------|---------------|
| `"NSE_EQ"`, `"NSE_FNO"`, etc. | `dhan.NSE` |
| `"BSE_EQ"`, `"BSE_FNO"`, etc. | `dhan.BSE` |
| `"MCX_COM"`, etc. | `dhan.MCX` |
| `"NCDEX_COM"`, etc. | `dhan.NCDEX` |

If constants are not available, the original string is used (backward compatibility).

## Date Format

All dates must be in `"YYYY-MM-DD"` format:
- ✅ `"2023-01-01"`
- ✅ `"2023-12-31"`
- ❌ `"01/01/2023"` (not supported)
- ❌ `"2023-1-1"` (use zero-padded)

## Error Handling

The implementation includes comprehensive error handling:
- Invalid access token
- Invalid security ID
- Invalid date format
- Network errors
- API errors from DhanHQ

All errors are returned in the response:
```json
{
    "success": false,
    "error": "Error message here"
}
```

## Testing

To test the implementation:

1. **Daily Data:**
```bash
curl -X POST "http://localhost:8000/api/trading/market/historical" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "your_token",
    "security_id": "1333",
    "exchange_segment": "NSE_EQ",
    "instrument_type": "EQUITY",
    "from_date": "2023-01-01",
    "to_date": "2023-01-31",
    "interval": "daily"
  }'
```

2. **Intraday Data:**
```bash
curl -X POST "http://localhost:8000/api/trading/market/historical" \
  -H "Content-Type: application/json" \
  -d '{
    "access_token": "your_token",
    "security_id": "1333",
    "exchange_segment": "NSE_EQ",
    "instrument_type": "EQUITY",
    "from_date": "2023-01-30",
    "to_date": "2023-01-31",
    "interval": "intraday"
  }'
```

## Notes

- The implementation follows the official DhanHQ-py example pattern exactly
- Backward compatibility is maintained for existing code
- Both string and integer security IDs are accepted
- Exchange constants are used when available, with fallback to strings
- Date validation should be added in the frontend for better UX

## Related Files

- `app/backend/trading.py` - Historical data service method
- `app/backend/main.py` - API endpoint and request model
- `app/frontend/src/services/api.js` - Frontend API service
- `app/frontend/src/components/trading/MarketData.jsx` - Frontend component (if exists)

