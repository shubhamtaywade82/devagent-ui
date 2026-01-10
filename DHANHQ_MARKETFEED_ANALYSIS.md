# DhanHQ MarketFeed Implementation Analysis

## Comparison: Official Example vs Current Implementation

### Official Example (from DhanHQ-py repository)

```python
from dhanhq import DhanContext, MarketFeed

# 1. Initialize Context
client_id = "YOUR_CLIENT_ID"
access_token = "YOUR_ACCESS_TOKEN"
dhan_context = DhanContext(client_id, access_token)

# 2. Define Instruments
# Format: (ExchangeSegment, SecurityID, InstrumentType)
instruments = [
    (MarketFeed.NSE, "1333", MarketFeed.Ticker),  # HDFC Bank Ticker
    (MarketFeed.NSE, "1333", MarketFeed.Quote),   # HDFC Bank Quote
    (MarketFeed.NSE, "1333", MarketFeed.Full),     # HDFC Bank Full Depth
]

# 3. Initialize Market Feed
version = "v2"  # Recommended version
market_feed = MarketFeed(dhan_context, instruments, version)

# 4. Run Forever
try:
    print("Connecting to Market Feed...")
    market_feed.run_forever()  # Blocking call
    # In a real application, you would consume data here
    # data = market_feed.get_data()
    # print(data)
except Exception as e:
    print(f"Error: {e}")
except KeyboardInterrupt:
    print("Market Feed Stopped")
finally:
    market_feed.disconnect()
```

### Current Implementation

**Location:** `app/backend/trading.py` (line 326-356)

**Key Differences:**

1. **DhanContext Usage:**
   - **Example:** Uses `DhanContext(client_id, access_token)` object
   - **Current:** Uses tuple `(client_id, access_token)`
   - **Impact:** May work but not following official pattern

2. **Instrument Format:**
   - **Example:** Uses constants `MarketFeed.NSE`, `MarketFeed.Ticker`, `MarketFeed.Quote`, `MarketFeed.Full`
   - **Current:** Uses numeric codes: `(exchange_code, security_id, feed_code)` where:
     - `exchange_code`: 1=NSE, 2=BSE, etc.
     - `feed_code`: 1=Ticker, 2=Quote, 3=Full
   - **Impact:** Numeric codes may work but constants are more readable and maintainable

3. **Security ID Format:**
   - **Example:** Uses string `"1333"`
   - **Current:** Converts to `int(security_id_str)`
   - **Impact:** May cause issues if SDK expects strings

4. **Version:**
   - **Example:** Uses `"v2"` (recommended)
   - **Current:** Defaults to `"v1"` but accepts `"v2"` from WebSocket request
   - **Impact:** Should default to `"v2"` to match recommendations

### Recommended Updates

#### 1. Update `create_market_feed` in `trading.py`

```python
def create_market_feed(self, access_token: str, instruments: List[tuple], version: str = "v2"):
    """
    Create Market Feed instance for real-time data

    Args:
        access_token: DhanHQ access token
        instruments: List of tuples in format [(exchange_code, security_id, feed_request_code), ...]
                   exchange_code: 1=NSE, 2=BSE, etc. OR use MarketFeed.NSE, MarketFeed.BSE constants
                   security_id: Security ID (as string or int)
                   feed_request_code: 1=Ticker, 2=Quote, 3=Full OR use MarketFeed.Ticker, MarketFeed.Quote, MarketFeed.Full
        version: API version ('v1' or 'v2', default 'v2')

    Returns:
        MarketFeed instance
    """
    if not self.client_id:
        raise ValueError("DHAN_CLIENT_ID is not configured")
    try:
        # Import MarketFeed and DhanContext
        try:
            from dhanhq.marketfeed import MarketFeed
            from dhanhq import DhanContext
        except ImportError:
            # Alternative import path
            from dhanhq import marketfeed
            from dhanhq import DhanContext
            MarketFeed = marketfeed.MarketFeed

        # Use DhanContext instead of tuple (per official example)
        dhan_context = DhanContext(self.client_id, access_token)

        # Convert instruments to use string security IDs if needed
        # The SDK may accept both formats, but example shows strings
        converted_instruments = []
        for inst in instruments:
            exchange_code, security_id, feed_code = inst
            # Keep security_id as string if it was originally a string
            # Otherwise convert to string to match example pattern
            security_id_str = str(security_id) if not isinstance(security_id, str) else security_id
            converted_instruments.append((exchange_code, security_id_str, feed_code))

        return MarketFeed(dhan_context, converted_instruments, version)
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Market Feed not available: {str(e)}")
```

#### 2. Consider Using Constants (Optional Enhancement)

If the MarketFeed class exposes constants, we could update the instrument conversion to use them:

```python
# In main.py, when creating instrument_tuples
try:
    from dhanhq.marketfeed import MarketFeed

    # Use constants instead of numeric codes
    exchange_constants = {
        0: MarketFeed.IDX_I,  # If available
        1: MarketFeed.NSE,
        2: MarketFeed.BSE,
        3: MarketFeed.MCX,
        4: MarketFeed.NCDEX,
    }

    feed_constants = {
        1: MarketFeed.Ticker,
        2: MarketFeed.Quote,
        3: MarketFeed.Full,
    }

    # Convert to use constants
    instrument_tuples = [
        (exchange_constants.get(exchange_code, MarketFeed.NSE),
         str(security_id),
         feed_constants.get(feed_code, MarketFeed.Quote))
        for exchange_code, security_id, feed_code in instrument_tuples
    ]
except ImportError:
    # Fallback to numeric codes if constants not available
    pass
```

### Current Implementation Status

✅ **Working:**
- WebSocket endpoint properly receives subscription requests
- Converts ExchangeSegment to exchange codes correctly
- Maps RequestCode (15, 17, 21) to feed codes (1, 2, 3)
- Handles both new and legacy formats
- Properly initializes MarketFeed and runs in background thread
- Uses `get_data()` to retrieve market data
- Properly handles disconnection

⚠️ **Potential Issues:**
- Using tuple instead of `DhanContext` object (may still work but not following official pattern)
- Converting security_id to int when example shows string
- Default version is "v1" instead of "v2"

### Testing Recommendations

1. Test with `DhanContext` instead of tuple
2. Test with string security IDs instead of integers
3. Verify that numeric codes still work (for backward compatibility)
4. Test with version "v2" as default

### API Documentation Notes

From the WebSocket API docs:
- RequestCode 15 = Ticker Packet
- RequestCode 17 = Quote Packet
- RequestCode 21 = Full Packet
- All responses are binary (Little Endian)
- Server sends ping every 10 seconds
- Connection closes if no pong for 40+ seconds

The MarketFeed SDK handles all of this internally, so we just need to ensure proper initialization and data retrieval.

