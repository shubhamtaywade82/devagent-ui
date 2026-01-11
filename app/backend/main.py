from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Union
import os
from dotenv import load_dotenv
import httpx
import json
import asyncio
import threading
from datetime import datetime, timedelta

# Try to import Ollama library, fall back to HTTP if not available
try:
    from ollama import AsyncClient
    OLLAMA_LIBRARY_AVAILABLE = True
except ImportError:
    OLLAMA_LIBRARY_AVAILABLE = False
    print("Warning: ollama library not installed. Using HTTP requests instead. Install with: pip install ollama")

from database import Database
from models import Project, File, ChatMessage
from trading import trading_service
from tools import DHANHQ_TOOLS
from tool_executor import execute_tool, get_access_token


def format_market_quote_result(data, instrument_name=None):
    """Format market quote data for LLM understanding

    Args:
        data: Market quote data from API
        instrument_name: Optional instrument name to use as fallback if symbol not found in quote data
    """
    if not data:
        return "No market data available"

    formatted = []
    quote_data = None

    # Debug: Log the structure we received
    print(f"[format_market_quote_result] Received data type: {type(data)}")
    if isinstance(data, dict):
        print(f"[format_market_quote_result] Top-level keys: {list(data.keys())}")
        # Log full structure for debugging (truncated if too large)
        data_str = json.dumps(data, indent=2)
        if len(data_str) > 1000:
            print(f"[format_market_quote_result] Data structure (first 1000 chars):\n{data_str[:1000]}...")
        else:
            print(f"[format_market_quote_result] Full data structure:\n{data_str}")
    elif isinstance(data, list):
        print(f"[format_market_quote_result] Data is a list with {len(data)} items")
        if len(data) > 0:
            print(f"[format_market_quote_result] First item: {json.dumps(data[0], indent=2)[:500]}")

    if isinstance(data, dict):
        # Try multiple possible response structures

        # Structure 1: data.data.data.{exchange_segment}.{security_id}
        if "data" in data and isinstance(data["data"], dict):
            if "data" in data["data"]:
                nested_data = data["data"]["data"]
                # Check if nested data is empty
                if isinstance(nested_data, dict) and len(nested_data) == 0:
                    return "No market data available. Possible reasons:\n1. Market is closed\n2. Security ID or exchange segment format is incorrect\n3. For indices like NIFTY, ensure you're using the correct security_id from search_instruments and exchange_segment 'IDX_I'\n\nTry searching for the instrument first using search_instruments to get the correct security_id and exchange_segment."

                # This is the nested structure: data.data.data.{exchange_segment}
                nested = nested_data
                print(f"[format_market_quote_result] Nested data keys: {list(nested.keys()) if isinstance(nested, dict) else 'not a dict'}")

                # Iterate through exchange segments (IDX_I, NSE_EQ, NSE_IDX, etc.)
                # Try IDX_I first for indices, then other segments
                for exchange_seg in ["IDX_I", "NSE_IDX", "BSE_IDX", "NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO"]:
                    if exchange_seg in nested:
                        securities = nested[exchange_seg]
                        print(f"[format_market_quote_result] Found segment {exchange_seg}, securities type: {type(securities)}")
                        if isinstance(securities, dict):
                            print(f"[format_market_quote_result] Security IDs in {exchange_seg}: {list(securities.keys())}")
                            # Iterate through security IDs
                            for security_id, quote_info in securities.items():
                                if isinstance(quote_info, dict) and quote_info:
                                    quote_data = quote_info
                                    print(f"[format_market_quote_result] Found quote data for security_id {security_id}, keys: {list(quote_data.keys())}")
                                    break
                            if quote_data:
                                break

                # If not found in specific segments, try all segments
                if not quote_data:
                    for exchange_seg, securities in nested.items():
                        if isinstance(securities, dict):
                            # Iterate through security IDs
                            for security_id, quote_info in securities.items():
                                if isinstance(quote_info, dict) and quote_info:
                                    quote_data = quote_info
                                    print(f"[format_market_quote_result] Found quote data in segment {exchange_seg}, security_id {security_id}")
                                    break
                            if quote_data:
                                break

        # Structure 2: Direct exchange segment keys (IDX_I, NSE_EQ, etc.) at top level
        if not quote_data:
            for exchange_seg in ["IDX_I", "NSE_IDX", "BSE_IDX", "NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO"]:
                if exchange_seg in data:
                    securities = data[exchange_seg]
                    if isinstance(securities, dict):
                        for security_id, quote_info in securities.items():
                            if isinstance(quote_info, dict) and quote_info:
                                quote_data = quote_info
                                print(f"[format_market_quote_result] Found quote data in top-level {exchange_seg}, security_id {security_id}")
                                break
                        if quote_data:
                            break

        # Structure 3: Direct flat structure
        if not quote_data:
            # Check if data itself contains quote fields
            if any(key in data for key in ["LTP", "ltp", "lastPrice", "OPEN", "open", "HIGH", "high"]):
                quote_data = data
                print(f"[format_market_quote_result] Using data as flat quote structure")

    # Extract quote information with multiple field name variations
    if quote_data and isinstance(quote_data, dict):
        # Try various field name formats from DhanHQ API
        # Check for OHLC structure first (some APIs return OHLC as nested object)
        ohlc_data = quote_data.get("ohlc") or quote_data.get("OHLC") or {}
        if not isinstance(ohlc_data, dict):
            ohlc_data = {}

        # Try to get symbol from quote data, with fallback to instrument_name parameter
        symbol = (quote_data.get("symbol") or quote_data.get("SYMBOL") or
                 quote_data.get("tradingSymbol") or quote_data.get("TRADING_SYMBOL") or
                 quote_data.get("trading_symbol") or quote_data.get("name") or
                 quote_data.get("NAME") or quote_data.get("instrumentName") or
                 quote_data.get("instrument_name") or quote_data.get("INSTRUMENT_NAME") or
                 quote_data.get("display_name") or quote_data.get("DISPLAY_NAME") or
                 instrument_name or "N/A")

        # LTP - try multiple variations
        ltp = (quote_data.get("LTP") or quote_data.get("ltp") or
              quote_data.get("lastPrice") or quote_data.get("LAST_PRICE") or
              quote_data.get("last_price") or quote_data.get("last_traded_price") or
              quote_data.get("currentPrice") or quote_data.get("CURRENT_PRICE") or "N/A")

        # Open - check OHLC first, then direct fields
        open_price = (ohlc_data.get("open") or ohlc_data.get("OPEN") or
                     quote_data.get("OPEN") or quote_data.get("open") or
                     quote_data.get("openPrice") or quote_data.get("OPEN_PRICE") or
                     quote_data.get("open_price") or "N/A")

        # High - check OHLC first, then direct fields
        high = (ohlc_data.get("high") or ohlc_data.get("HIGH") or
               quote_data.get("HIGH") or quote_data.get("high") or
               quote_data.get("highPrice") or quote_data.get("HIGH_PRICE") or
               quote_data.get("high_price") or "N/A")

        # Low - check OHLC first, then direct fields
        low = (ohlc_data.get("low") or ohlc_data.get("LOW") or
              quote_data.get("LOW") or quote_data.get("low") or
              quote_data.get("lowPrice") or quote_data.get("LOW_PRICE") or
              quote_data.get("low_price") or "N/A")

        # Close - check OHLC first, then direct fields
        close = (ohlc_data.get("close") or ohlc_data.get("CLOSE") or
                quote_data.get("CLOSE") or quote_data.get("close") or
                quote_data.get("closePrice") or quote_data.get("CLOSE_PRICE") or
                quote_data.get("previousClose") or quote_data.get("PREV_CLOSE") or
                quote_data.get("prev_close") or quote_data.get("prevClose") or "N/A")

        # Volume - try multiple variations, including checking if it's 0 or None
        volume = None
        for key in ["VOLUME", "volume", "totalVolume", "TOTAL_VOLUME", "total_volume",
                   "tradedVolume", "TRADED_VOLUME", "VOL", "vol", "TURNOVER", "turnover"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    volume_val = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if volume_val is not None and volume_val >= 0:  # Allow 0 as valid volume
                        volume = volume_val
                        break
                except (ValueError, TypeError):
                    continue
        volume = volume if volume is not None else "N/A"

        # Format volume if it's a number
        if isinstance(volume, (int, float)):
            # Format large numbers with commas
            if volume >= 1000000:
                volume = f"{volume/1000000:.2f}M"
            elif volume >= 1000:
                volume = f"{volume/1000:.2f}K"
            else:
                volume = f"{volume:.0f}"

        # Format numeric values properly
        def format_price(value):
            if value == "N/A" or value is None:
                return "N/A"
            try:
                if isinstance(value, str):
                    value = float(value)
                return f"{value:.2f}" if value != 0 else "N/A"
            except (ValueError, TypeError):
                return "N/A"

        ltp = format_price(ltp)
        open_price = format_price(open_price)
        high = format_price(high)
        low = format_price(low)
        close = format_price(close)

        # Format the output
        formatted.append(f"""
Symbol: {symbol}
Current Price (LTP): ₹{ltp}
Open: ₹{open_price}
High: ₹{high}
Low: ₹{low}
Previous Close: ₹{close}
Volume: {volume}
""")
    else:
        # If we couldn't find quote_data, log what we received
        print(f"[format_market_quote_result] Could not extract quote_data. Data structure: {json.dumps(data, indent=2)[:500]}")

        # Try one more structure: check if data is a list with quote objects
        if isinstance(data, list) and len(data) > 0:
            print(f"[format_market_quote_result] Data is a list, trying first item as quote_data")
            first_item = data[0]
            if isinstance(first_item, dict):
                quote_data = first_item
                # Re-run extraction with this quote_data
                # (We'll handle this by checking quote_data again below)

        # If still no quote_data, return detailed error with raw structure
        if not quote_data:
            # Show raw structure for debugging
            raw_structure = json.dumps(data, indent=2)
            if len(raw_structure) > 2000:
                raw_structure = raw_structure[:2000] + "... (truncated)"

            return f"""No market data available.

**Debugging Information:**
The API returned data, but it doesn't match expected structures. Here's what was received:

```json
{raw_structure}
```

**Possible reasons:**
1. Market is closed (indices may not have data outside trading hours)
2. API response structure changed
3. Security ID or exchange segment format issue

**Troubleshooting:**
- Check if market is open (9:15 AM - 3:30 PM IST)
- Verify security_id={instrument_name or 'N/A'} and exchange_segment are correct
- Try using the REST API endpoint directly: `/api/trading/market/quote`
"""

    # If we couldn't find the data, return detailed error with raw structure
    if not formatted:
        # Show raw structure for debugging
        raw_structure = json.dumps(data, indent=2)
        if len(raw_structure) > 2000:
            raw_structure = raw_structure[:2000] + "... (truncated)"

        # Check if it's actually empty (market closed scenario)
        is_empty = False
        if isinstance(data, dict):
            if "data" in data:
                if isinstance(data["data"], dict):
                    if "data" in data["data"]:
                        nested = data["data"]["data"]
                        is_empty = isinstance(nested, dict) and len(nested) == 0
                    else:
                        is_empty = len(data["data"]) == 0
                else:
                    is_empty = not data["data"]
            else:
                is_empty = len(data) == 0

        if is_empty:
            return f"""No market data available.

**Possible reasons:**
1. **Market is closed** - Indian stock market hours are 9:15 AM - 3:30 PM IST (Monday-Friday)
2. **Weekend/Holiday** - Markets are closed on weekends and public holidays
3. **API returned empty response** - The DhanHQ API may not have data for this instrument at this time

**Debugging info:**
- Instrument: {instrument_name or 'NIFTY'}
- Security ID: 13
- Exchange: IDX_I
- Response structure: Empty or null data

**What to try:**
- Check if market is currently open
- Verify the security_id and exchange_segment are correct
- Try again during market hours (9:15 AM - 3:30 PM IST)

**Raw API Response:**
```json
{raw_structure}
```"""
        else:
            return f"""No market data available.

**Debugging Information:**
The API returned data, but it doesn't match expected structures. Here's what was received:

```json
{raw_structure}
```

**Possible reasons:**
1. Market is closed (indices may not have data outside trading hours)
2. API response structure changed
3. Security ID or exchange segment format issue

**Troubleshooting:**
- Check if market is open (9:15 AM - 3:30 PM IST)
- Verify security_id and exchange_segment are correct
- Check backend logs for `[get_market_quote]` and `[format_market_quote_result]` entries"""

    # Try to extract any numeric values that might be prices (fallback)
    if not formatted:
        if isinstance(data, dict):
            # Look for any numeric fields that might be prices
            for key, value in data.items():
                if isinstance(value, (int, float)) and value > 0:
                    formatted.append(f"{key}: {value}")

        if not formatted:
            # Last resort: return formatted JSON with helpful message
            raw_json = json.dumps(data, indent=2)
            # Limit the output size for readability
            if len(raw_json) > 2000:
                raw_json = raw_json[:2000] + "\n... (truncated)"

            # Check if this might be an error response
            if isinstance(data, dict):
                if data.get("status") == "failure" or "error" in str(data).lower():
                    error_info = data.get("remarks") or data.get("data") or data.get("error") or {}
                    error_code = error_info.get("error_code") if isinstance(error_info, dict) else None
                    error_message = error_info.get("error_message") if isinstance(error_info, dict) else str(error_info)
                    if error_code or error_message:
                        return f"Market data request failed. Error: {error_code or ''} {error_message or ''}\n\nPossible reasons:\n1. Market is closed\n2. Invalid security ID or exchange segment\n3. For indices like NIFTY, ensure you're using security_id=13 and exchange_segment='IDX_I'\n4. Access token may be invalid or expired"

            return f"Market data received but format not recognized. This might indicate:\n1. Market is closed\n2. API response format has changed\n3. Security ID or exchange segment is incorrect\n4. For indices like NIFTY, ensure you're using security_id=13 and exchange_segment='IDX_I'\n\nRaw response data (for debugging):\n{raw_json}"

    return "\n".join(formatted) if formatted else "No market data available. Possible reasons:\n1. Market is closed\n2. Security ID or exchange segment format is incorrect\n3. For indices like NIFTY, ensure you're using the correct security_id from search_instruments and exchange_segment 'IDX_I'\n\nTry searching for the instrument first using search_instruments to get the correct security_id and exchange_segment."


def format_positions_result(data):
    """Format positions data for LLM understanding"""
    if not data or not isinstance(data, list):
        return "No positions data available"

    if len(data) == 0:
        return "No open positions"

    formatted = ["Current Open Positions:\n"]
    total_pnl = 0

    for pos in data:
        symbol = pos.get("symbol") or pos.get("tradingSymbol", "Unknown")
        quantity = pos.get("quantity") or pos.get("qty", 0)
        avg_price = pos.get("averagePrice") or pos.get("avgPrice", 0)
        ltp = pos.get("ltp") or pos.get("lastPrice", 0)
        pnl = pos.get("pnl") or pos.get("profitLoss", 0)
        total_pnl += float(pnl) if pnl else 0

        formatted.append(f"""
- {symbol}
  Quantity: {quantity}
  Average Price: ₹{avg_price}
  Current Price: ₹{ltp}
  P&L: ₹{pnl}
""")

    formatted.append(f"\nTotal P&L: ₹{total_pnl:.2f}")
    return "\n".join(formatted)


def format_holdings_result(data):
    """Format holdings data for LLM understanding"""
    if not data or not isinstance(data, list):
        return "No holdings data available"

    if len(data) == 0:
        return "No holdings"

    formatted = ["Current Holdings:\n"]
    total_value = 0

    for holding in data:
        symbol = holding.get("symbol") or holding.get("tradingSymbol", "Unknown")
        quantity = holding.get("quantity") or holding.get("qty", 0)
        avg_price = holding.get("averagePrice") or holding.get("avgPrice", 0)
        ltp = holding.get("ltp") or holding.get("lastPrice", 0)
        value = float(ltp) * float(quantity) if ltp and quantity else 0
        total_value += value

        formatted.append(f"""
- {symbol}
  Quantity: {quantity}
  Average Price: ₹{avg_price}
  Current Price: ₹{ltp}
  Current Value: ₹{value:.2f}
""")

    formatted.append(f"\nTotal Portfolio Value: ₹{total_value:.2f}")
    return "\n".join(formatted)


def format_search_results(data):
    """Format instrument search results for LLM understanding"""
    if not data or not isinstance(data, dict):
        return "No search results available"

    instruments = data.get("instruments", [])
    if not instruments or len(instruments) == 0:
        return f"No instruments found for query: {data.get('query', '')}"

    formatted = [f"Found {len(instruments)} instrument(s):\n"]

    for inst in instruments:
        symbol = inst.get("display_name") or inst.get("symbol_name") or inst.get("trading_symbol", "Unknown")
        security_id = inst.get("security_id")
        exchange_segment = inst.get("exchange_segment", "N/A")
        instrument_type = inst.get("instrument_type", "")

        formatted.append(f"""
- {symbol}
  Security ID: {security_id}
  Exchange Segment: {exchange_segment}
  Type: {instrument_type}

  Use this security_id ({security_id}) and exchange_segment ({exchange_segment}) for:
  - get_market_quote: {{"{exchange_segment}": [{security_id}]}}
  - get_historical_data: security_id={security_id}, exchange_segment="{exchange_segment}"
  - get_option_chain: under_security_id={security_id}, under_exchange_segment="{exchange_segment}"
""")

    formatted.append("\nSelect the appropriate instrument from above and use its security_id and exchange_segment for subsequent operations.")
    return "\n".join(formatted)

load_dotenv()

app = FastAPI(title="DevAgent API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
db = Database()

# Background task for weekly instrument updates
async def weekly_instrument_sync():
    """Background task to sync instruments weekly"""
    while True:
        try:
            # Wait 7 days (604800 seconds)
            await asyncio.sleep(604800)

            # Sync instruments
            db_instance = Database()
            result = await trading_service.sync_instruments_to_db(db_instance, "detailed")
            if result.get("success"):
                print(f"Instruments synced successfully: {result['data']['synced_count']} instruments")
            else:
                print(f"Instrument sync failed: {result.get('error')}")
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in weekly instrument sync: {e}")

# Global variable for sync task
sync_task = None

@app.on_event("startup")
async def startup_event():
    """Initialize instruments on startup"""
    global sync_task
    db_instance = Database()

    # Ensure indexes are created for performance
    await db_instance.ensure_indexes()

    # Check if instruments exist, sync if needed
    instruments_exist = await db_instance.instruments_exist("detailed")
    if not instruments_exist:
        print("No instruments in database, performing initial sync...")
        try:
            result = await trading_service.sync_instruments_to_db(db_instance, "detailed")
            if result.get("success"):
                print(f"Initial instrument sync completed: {result['data']['synced_count']} instruments")
            else:
                print(f"Initial instrument sync failed: {result.get('error')}")
        except Exception as e:
            print(f"Error in initial instrument sync: {e}")
    else:
        metadata = await db_instance.get_instruments_metadata()
        if metadata:
            print(f"Instruments in database: {metadata.get('count', 0)} instruments, last updated: {metadata.get('last_updated', 'unknown')}")

    # Start weekly sync task
    sync_task = asyncio.create_task(weekly_instrument_sync())

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global sync_task
    if sync_task:
        sync_task.cancel()
        try:
            await sync_task
        except asyncio.CancelledError:
            pass

# AI Provider configuration
# Use Ollama directly at localhost:11434 (default Ollama port)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
# OpenAI-compatible API (e.g., Open WebUI, vLLM, Ollama Router, etc.)
# Set to None to use Ollama directly instead
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", None)  # e.g., "http://localhost:8080/v1"
OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "nemesis-coder")
# Ollama Router native endpoint (alternative to OpenAI-compatible)
# Set to None to use Ollama directly instead
OLLAMA_ROUTER_BASE = os.getenv("OLLAMA_ROUTER_BASE", None)  # e.g., "http://localhost:8080"
# Use OpenAI-compatible API if configured, otherwise fall back to Ollama
# Set to "false" to use Ollama directly at localhost:11434
USE_OPENAI_API = os.getenv("USE_OPENAI_API", "false").lower() == "true"
# Use Ollama Router native endpoint (supports X-Task header for specialized tasks)
# Set to "false" to use Ollama directly at localhost:11434
USE_OLLAMA_ROUTER = os.getenv("USE_OLLAMA_ROUTER", "false").lower() == "true"


# Request/Response Models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""


class FileCreate(BaseModel):
    project_id: str
    path: str
    content: str


class FileDelete(BaseModel):
    project_id: str
    path: str


class ChatRequest(BaseModel):
    message: str
    project_id: Optional[str] = None
    context: Optional[List[str]] = []
    task: Optional[str] = None  # e.g., "options" for options analysis with X-Task header
    access_token: Optional[str] = None  # DhanHQ access token for trading operations


class ComponentGenerateRequest(BaseModel):
    description: str
    framework: str = "react"


class DesignSystemRequest(BaseModel):
    description: str
    style: str = "modern"


# Trading Request Models
class TradingAuthRequest(BaseModel):
    pin: Optional[str] = None
    totp: Optional[str] = None
    token_id: Optional[str] = None


class PlaceOrderRequest(BaseModel):
    access_token: str
    security_id: str
    exchange_segment: str
    transaction_type: str
    quantity: int
    order_type: str
    product_type: str
    price: float = 0
    trigger_price: float = 0
    disclosed_quantity: int = 0
    validity: str = "DAY"


class ModifyOrderRequest(BaseModel):
    access_token: str
    order_id: str
    order_type: Optional[str] = None
    leg_name: Optional[str] = None
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    disclosed_quantity: Optional[int] = None
    validity: Optional[str] = None


class MarketQuoteRequest(BaseModel):
    access_token: Optional[str] = None  # Optional - can use DHAN_ACCESS_TOKEN env var as fallback
    securities: dict


class OptionChainRequest(BaseModel):
    access_token: str
    under_security_id: int
    under_exchange_segment: str
    expiry: str


class ExpiryListRequest(BaseModel):
    access_token: str
    under_security_id: int
    under_exchange_segment: str


class HistoricalDataRequest(BaseModel):
    access_token: Optional[str] = None  # Optional - can use DHAN_ACCESS_TOKEN env var as fallback
    security_id: Union[int, str]  # Accept both int and string (official example uses string)
    exchange_segment: str
    instrument_type: str
    from_date: str  # Format: "YYYY-MM-DD"
    to_date: str    # Format: "YYYY-MM-DD"
    interval: str = "daily"  # "daily" for daily data, "intraday" or "minute" for intraday minute data


class TradeHistoryRequest(BaseModel):
    access_token: str
    from_date: str
    to_date: str
    page_number: int = 0


class MarginCalculatorRequest(BaseModel):
    access_token: str
    security_id: str
    exchange_segment: str
    transaction_type: str
    quantity: int
    product_type: str
    price: float = 0
    trigger_price: float = 0


class KillSwitchRequest(BaseModel):
    token_id: str
    status: Optional[str] = None  # ACTIVATE or DEACTIVATE, None for get status


class LedgerRequest(BaseModel):
    access_token: str
    from_date: Optional[str] = None
    to_date: Optional[str] = None


class InstrumentListCSVRequest(BaseModel):
    format_type: str = "detailed"  # "compact" or "detailed"


class InstrumentListSegmentwiseRequest(BaseModel):
    exchange_segment: str  # e.g., "NSE_EQ", "BSE_EQ", "MCX_COM"
    access_token: Optional[str] = None  # Optional - not required for this endpoint


# Health check
@app.get("/")
async def root():
    return {"status": "ok", "message": "DevAgent API is running"}


# Projects endpoints
@app.post("/api/projects", response_model=dict)
async def create_project(project: ProjectCreate):
    try:
        project_data = {
            "name": project.name,
            "description": project.description,
            "created_at": None,
            "updated_at": None
        }
        project_id = await db.create_project(project_data)
        # Fetch the created project to get properly serialized data
        created_project = await db.get_project(project_id)
        if not created_project:
            raise HTTPException(status_code=500, detail="Failed to retrieve created project")
        return created_project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects", response_model=List[dict])
async def list_projects():
    try:
        projects = await db.get_all_projects()
        return projects
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/{project_id}", response_model=dict)
async def get_project(project_id: str):
    try:
        project = await db.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    try:
        result = await db.delete_project(project_id)
        if not result:
            raise HTTPException(status_code=404, detail="Project not found")
        # Also delete all files in the project
        await db.delete_files_by_project(project_id)
        return {"message": "Project deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Files endpoints
@app.post("/api/files", response_model=dict)
async def save_file(file: FileCreate):
    try:
        file_data = {
            "project_id": file.project_id,
            "path": file.path,
            "content": file.content,
            "updated_at": None
        }
        file_id = await db.save_file(file_data)
        # Fetch the saved file to get properly serialized data
        saved_file = await db.get_file(file.project_id, file.path)
        if not saved_file:
            raise HTTPException(status_code=500, detail="Failed to retrieve saved file")
        return saved_file
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files/{project_id}", response_model=List[dict])
async def get_files(project_id: str):
    try:
        files = await db.get_files_by_project(project_id)
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/files")
async def delete_file(file: FileDelete):
    try:
        result = await db.delete_file(file.project_id, file.path)
        if not result:
            raise HTTPException(status_code=404, detail="File not found")
        return {"message": "File deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# AI Chat endpoints
async def generate_openai_response_stream(prompt: str):
    """Generate streaming response from OpenAI-compatible API"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"
            payload = {
                "model": OPENAI_API_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": True
            }

            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"⚠️ Error: {error_text.decode()}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        if line.strip() == "data: [DONE]":
                            yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                            break
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])  # Remove "data: " prefix
                                if "choices" in data and len(data["choices"]) > 0:
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")

                                    # Check for error patterns in content
                                    if content:
                                        error_patterns = [
                                            "[router error:",
                                            "router error:",
                                            "RuntimeError",
                                            "error:",
                                        ]
                                        is_error = any(pattern.lower() in content.lower() for pattern in error_patterns)

                                        if is_error:
                                            error_msg = f"⚠️ API Error: {content.strip()}"
                                            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                                            return
                                        else:
                                            yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"

                                    # Check if finished
                                    finish_reason = data["choices"][0].get("finish_reason")
                                    if finish_reason:
                                        yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                                        break
                            except json.JSONDecodeError:
                                continue
    except httpx.ConnectError:
        error_msg = f"⚠️ OpenAI-compatible API is not reachable at {OPENAI_API_BASE}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"


async def generate_ollama_router_response(prompt: str, task: Optional[str] = None, model: Optional[str] = None):
    """Generate non-streaming response from Ollama Router native endpoint"""
    if OLLAMA_LIBRARY_AVAILABLE:
        # Use Ollama Python library if available
        try:
            headers = {}
            if task:
                headers["X-Task"] = task

            client = AsyncClient(host=OLLAMA_ROUTER_BASE, headers=headers)
            messages = [{"role": "user", "content": prompt}]

            response = await client.chat(
                model=model or OPENAI_API_MODEL,
                messages=messages,
                stream=False
            )

            content = response.get('message', {}).get('content', '')
            return {"response": content}
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "refused" in error_msg.lower():
                raise HTTPException(status_code=503, detail=f"Ollama Router is not reachable at {OLLAMA_ROUTER_BASE}")
            raise HTTPException(status_code=500, detail=error_msg)

    # Fallback to HTTP requests if library not available
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_ROUTER_BASE}/api/chat"
            payload = {
                "model": model or OPENAI_API_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "stream": False
            }

            headers = {}
            if task:
                headers["X-Task"] = task

            response = await client.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            data = response.json()
            # Ollama Router native format
            if "message" in data:
                return {"response": data["message"]["content"]}
            elif "response" in data:
                return {"response": data["response"]}
            return {"response": ""}
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Ollama Router is not reachable at {OLLAMA_ROUTER_BASE}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_openai_response(prompt: str, tools=None, messages=None, access_token=None):
    """Generate non-streaming response from OpenAI-compatible API with optional tool calling"""
    # Use provided token or fallback to environment variable
    access_token = get_access_token(access_token)
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OPENAI_API_BASE}/chat/completions"

            # Build messages list
            if messages is None:
                messages = [{"role": "user", "content": prompt}]

            payload = {
                "model": OPENAI_API_MODEL,
                "messages": messages,
                "stream": False
            }

            # Add tools if provided
            if tools:
                payload["tools"] = tools
                # For trading requests, force tool usage if the query is about prices/positions
                # Check all user messages for trading-related keywords
                user_messages = [msg.get("content", "").lower() for msg in messages if msg.get("role") == "user"]
                combined_user_content = " ".join(user_messages)

                trading_keywords = [
                    "price", "quote", "position", "positions", "holding", "holdings",
                    "p&l", "pnl", "profit", "loss", "portfolio", "balance", "fund",
                    "funds", "margin", "order", "orders", "trade", "trades",
                    "nifty", "hdfc", "reliance", "tcs", "infy", "sensex", "bank nifty",
                    "current", "what are", "show me", "get my", "fetch", "search"
                ]

                if access_token and any(keyword in combined_user_content for keyword in trading_keywords):
                    # Force tool usage for trading-related queries
                    payload["tool_choice"] = "required"
                else:
                    payload["tool_choice"] = "auto"  # Let model decide when to use tools

            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            data = response.json()

            # Extract content from OpenAI format
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0]["message"]

                # Check if model wants to call a function
                if "tool_calls" in message and message["tool_calls"]:
                    # Execute function calls
                    tool_results = []
                    # Track instrument name from search_instruments for use in get_market_quote
                    instrument_name_from_search = None

                    # Track tool calls for UI display
                    tool_calls_metadata = []

                    # Send initial planning step (if streaming)
                    # Note: This is for non-streaming response, streaming happens in chat_stream

                    for tool_call in message["tool_calls"]:
                        function_name = tool_call["function"]["name"]
                        try:
                            function_args = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            function_args = {}

                        # Format tool call details for user visibility
                        tool_call_details = f"🔧 Using tool: **{function_name}**\n"
                        if function_args:
                            # Format arguments nicely, hiding sensitive data
                            formatted_args = {}
                            for key, value in function_args.items():
                                if key == "access_token" or "token" in key.lower():
                                    formatted_args[key] = "***"  # Hide tokens
                                elif isinstance(value, dict) and len(str(value)) > 200:
                                    formatted_args[key] = f"<dict with {len(value)} keys>"
                                elif isinstance(value, list) and len(value) > 10:
                                    formatted_args[key] = f"<list with {len(value)} items>"
                                else:
                                    formatted_args[key] = value
                            tool_call_details += f"📋 Parameters: `{json.dumps(formatted_args, indent=2)}`\n"
                        tool_call_details += "⏳ Executing...\n"

                        # Store tool call metadata for UI
                        tool_call_meta = {
                            "tool": function_name,
                            "args": formatted_args if function_args else {},
                            "status": "executing",
                            "timestamp": datetime.now().isoformat()
                        }

                        # Execute the tool
                        result = await execute_tool(function_name, function_args, access_token)

                        # Update tool call metadata with result
                        tool_call_meta["status"] = "success" if result.get("success") else "error"
                        tool_call_meta["result"] = result.get("error") if not result.get("success") else "Success"
                        tool_calls_metadata.append(tool_call_meta)

                        # Format result for better LLM understanding
                        if isinstance(result, dict):
                            if result.get("success"):
                                # Format successful result
                                data = result.get("data", {})
                                if function_name == "search_instruments" or function_name == "find_instrument":
                                    # Format search results nicely
                                    formatted_result = format_search_results(data)
                                    # Extract instrument name from search results for later use
                                    if data.get("instruments") and len(data["instruments"]) > 0:
                                        inst = data["instruments"][0]
                                        instrument_name_from_search = (inst.get("display_name") or
                                                                     inst.get("symbol_name") or
                                                                     inst.get("trading_symbol") or
                                                                     None)
                                elif function_name == "get_market_quote" or function_name == "get_quote":
                                    # Log the raw data before formatting for debugging
                                    print(f"[get_market_quote] Raw data before formatting: {json.dumps(data, indent=2)[:1000]}")
                                    # Format market quote data nicely, using instrument name from search if available
                                    formatted_result = format_market_quote_result(data, instrument_name=instrument_name_from_search)

                                    # If formatting failed (returns "No market data available"), include raw structure
                                    if formatted_result.startswith("No market data available"):
                                        raw_data_str = json.dumps(data, indent=2)
                                        if len(raw_data_str) > 1500:
                                            raw_data_str = raw_data_str[:1500] + "... (truncated)"
                                        formatted_result = f"{formatted_result}\n\n**Raw API Response:**\n```json\n{raw_data_str}\n```"
                                elif function_name == "analyze_market":
                                    # Format market analysis result with trend information
                                    if data.get("formatted_analysis"):
                                        formatted_result = data["formatted_analysis"]
                                    elif data.get("metrics"):
                                        metrics = data["metrics"]
                                        trend = metrics.get("trend", {})
                                        if trend:
                                            formatted_result = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\n{metrics.get('trend_summary', '')}"
                                        else:
                                            formatted_result = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\nHistorical data available but trend calculation failed."
                                    else:
                                        formatted_result = json.dumps(data, indent=2)
                                elif function_name == "get_historical_data":
                                    # Format historical data for trend analysis
                                    if isinstance(data, list) and len(data) > 0:
                                        # Show summary of historical data
                                        first = data[0] if isinstance(data[0], dict) else {}
                                        last = data[-1] if isinstance(data[-1], dict) else {}
                                        first_close = first.get("close") or first.get("CLOSE") or "N/A"
                                        last_close = last.get("close") or last.get("CLOSE") or "N/A"
                                        formatted_result = f"Historical Data ({len(data)} data points):\nFirst Close: ₹{first_close}\nLast Close: ₹{last_close}"
                                        if isinstance(first_close, (int, float)) and isinstance(last_close, (int, float)) and first_close > 0:
                                            change = last_close - first_close
                                            change_pct = (change / first_close) * 100
                                            formatted_result += f"\nChange: ₹{change:.2f} ({change_pct:+.2f}%)\nDirection: {'📈 Upward' if change > 0 else '📉 Downward' if change < 0 else '➡️ Neutral'}"
                                    else:
                                        formatted_result = json.dumps(data, indent=2)
                                elif function_name == "get_positions":
                                    formatted_result = format_positions_result(data)
                                elif function_name == "get_holdings":
                                    formatted_result = format_holdings_result(data)
                                else:
                                    formatted_result = json.dumps(data, indent=2)

                                # Include tool call details in successful response
                                content = f"{tool_call_details}✅ Success!\n\n{formatted_result}"
                            else:
                                # Format error - include sample instruments if available
                                error_msg = result.get("error", "Unknown error")
                                error_data = result.get("data", {})
                                sample_instruments = error_data.get("sample_instruments")

                                if sample_instruments:
                                    # Add sample instruments to error message
                                    sample_text = "\n\nAvailable instruments from API:\n"
                                    for inst in sample_instruments[:10]:
                                        sample_text += f"  - {inst.get('symbol_name', 'N/A')} (underlying_symbol: {inst.get('underlying_symbol', 'N/A')}, security_id: {inst.get('security_id', 'N/A')})\n"
                                    error_msg += sample_text

                                # Include tool call details in error response
                                content = f"{tool_call_details}❌ Error: {error_msg}"
                        else:
                            content = f"{tool_call_details}\n{json.dumps(result, indent=2)}"

                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": function_name,
                            "content": content
                        })

                    # Add assistant message with tool calls and tool results
                    messages.append(message)
                    messages.extend(tool_results)

                    # AGENTIC LOOP: Allow multiple rounds of tool calls
                    # The LLM can make more tool calls based on previous results
                    max_iterations = 5  # Prevent infinite loops
                    iteration = 0

                    while iteration < max_iterations:
                        iteration += 1
                        print(f"[agentic_loop] Iteration {iteration}/{max_iterations}")

                        # Get response with tool results
                        payload["messages"] = messages
                        # Keep tools available for next iteration
                        if tools:
                            payload["tools"] = tools
                            payload["tool_choice"] = "auto"  # Let model decide if more tools needed

                        response = await client.post(url, json=payload)
                        if response.status_code != 200:
                            raise HTTPException(status_code=response.status_code, detail=response.text)
                        data = response.json()

                        if "choices" not in data or len(data["choices"]) == 0:
                            break

                        next_message = data["choices"][0]["message"]

                        # Check if model wants to make more tool calls
                        if "tool_calls" in next_message and next_message["tool_calls"]:
                            print(f"[agentic_loop] Model wants to make {len(next_message['tool_calls'])} more tool call(s)")

                            # Execute the new tool calls
                            new_tool_results = []
                            for tool_call in next_message["tool_calls"]:
                                function_name = tool_call["function"]["name"]
                                try:
                                    function_args = json.loads(tool_call["function"]["arguments"])
                                except json.JSONDecodeError:
                                    function_args = {}

                                print(f"[agentic_loop] Executing: {function_name} with args: {json.dumps(function_args, indent=2)[:200]}")

                                # Execute the tool
                                result = await execute_tool(function_name, function_args, access_token)

                                # Format result
                                if isinstance(result, dict):
                                    if result.get("success"):
                                        data = result.get("data", {})
                                        # Use same formatting logic as before
                                        if function_name == "search_instruments" or function_name == "find_instrument":
                                            formatted_result = format_search_results(data)
                                        elif function_name == "get_market_quote" or function_name == "get_quote":
                                            # Log the raw data before formatting for debugging
                                            print(f"[agentic_loop] get_market_quote raw data: {json.dumps(data, indent=2)[:1000]}")
                                            formatted_result = format_market_quote_result(data, instrument_name=instrument_name_from_search)

                                            # If formatting failed (returns "No market data available"), include raw structure
                                            if formatted_result.startswith("No market data available"):
                                                raw_data_str = json.dumps(data, indent=2)
                                                if len(raw_data_str) > 1500:
                                                    raw_data_str = raw_data_str[:1500] + "... (truncated)"
                                                formatted_result = f"{formatted_result}\n\n**Raw API Response:**\n```json\n{raw_data_str}\n```"
                                        elif function_name == "analyze_market":
                                            if data.get("formatted_analysis"):
                                                formatted_result = data["formatted_analysis"]
                                            elif data.get("metrics"):
                                                metrics = data["metrics"]
                                                trend = metrics.get("trend", {})
                                                if trend:
                                                    formatted_result = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\n{metrics.get('trend_summary', '')}"
                                                else:
                                                    formatted_result = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\nHistorical data available but trend calculation failed."
                                            else:
                                                formatted_result = json.dumps(data, indent=2)
                                        elif function_name == "get_historical_data":
                                            if isinstance(data, list) and len(data) > 0:
                                                first = data[0] if isinstance(data[0], dict) else {}
                                                last = data[-1] if isinstance(data[-1], dict) else {}
                                                first_close = first.get("close") or first.get("CLOSE") or "N/A"
                                                last_close = last.get("close") or last.get("CLOSE") or "N/A"
                                                formatted_result = f"Historical Data ({len(data)} data points):\nFirst Close: ₹{first_close}\nLast Close: ₹{last_close}"
                                                if isinstance(first_close, (int, float)) and isinstance(last_close, (int, float)) and first_close > 0:
                                                    change = last_close - first_close
                                                    change_pct = (change / first_close) * 100
                                                    formatted_result += f"\nChange: ₹{change:.2f} ({change_pct:+.2f}%)\nDirection: {'📈 Upward' if change > 0 else '📉 Downward' if change < 0 else '➡️ Neutral'}"
                                            else:
                                                formatted_result = json.dumps(data, indent=2)
                                        else:
                                            formatted_result = json.dumps(data, indent=2)
                                        content = f"✅ Success!\n\n{formatted_result}"
                                    else:
                                        error_msg = result.get("error", "Unknown error")
                                        content = f"❌ Error: {error_msg}"
                                else:
                                    content = json.dumps(result, indent=2)

                                new_tool_results.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "name": function_name,
                                    "content": content
                                })

                                # Update tool calls metadata for UI
                                tool_calls_metadata.append({
                                    "tool": function_name,
                                    "args": function_args,
                                    "status": "success" if (isinstance(result, dict) and result.get("success")) else "error",
                                    "result": content[:200],
                                    "timestamp": datetime.now().isoformat()
                                })

                            # Add assistant message with tool calls and tool results
                            messages.append(next_message)
                            messages.extend(new_tool_results)

                            # Continue loop to see if model wants to make more calls
                            continue
                        else:
                            # No more tool calls - model has final answer
                            final_content = next_message.get("content", "")
                            print(f"[agentic_loop] Final response after {iteration} iteration(s)")

                            # Include tool calls metadata in response for UI display
                            return {
                                "response": final_content,
                                "tool_calls": tool_calls_metadata if tool_calls_metadata else [],
                                "reasoning": f"Used {len(tool_calls_metadata)} tool(s) in {iteration} iteration(s) to answer your question" if tool_calls_metadata else None
                            }

                    # If we hit max iterations, return the last response
                    if "choices" in data and len(data["choices"]) > 0:
                        final_message = data["choices"][0]["message"]
                        final_content = final_message.get("content", "Reached maximum iterations. Please try a simpler query.")
                        return {
                            "response": final_content,
                            "tool_calls": tool_calls_metadata if tool_calls_metadata else [],
                            "reasoning": f"Used {len(tool_calls_metadata)} tool(s) in {max_iterations} iteration(s)" if tool_calls_metadata else None
                        }

                # If no tool calls but tools were available and this is a trading query,
                # the model might have ignored tools - try fallback extraction or force tool usage
                content = message.get("content", "")
                if tools and access_token:
                    # Check if model showed code instead of calling tools
                    import re

                    # Check for common trading queries that should use tools
                    user_message = messages[-1].get("content", "").lower() if messages else ""

                    # If user asked about positions and no tool was called, force get_positions
                    if ("position" in user_message or "positions" in user_message) and "tool_calls" not in message:
                        print("Detected positions query but no tool call - forcing get_positions")
                        result = await execute_tool("get_positions", {}, access_token)
                        if result.get("success"):
                            formatted = format_positions_result(result.get("data", {}))
                            return {"response": f"Here are your current positions:\n\n{formatted}"}
                        else:
                            error_msg = result.get("error", "Unknown error")
                            return {"response": f"Failed to fetch positions: {error_msg}"}

                    # If user asked about holdings and no tool was called, force get_holdings
                    if ("holding" in user_message or "holdings" in user_message) and "tool_calls" not in message:
                        print("Detected holdings query but no tool call - forcing get_holdings")
                        result = await execute_tool("get_holdings", {}, access_token)
                        if result.get("success"):
                            formatted = format_holdings_result(result.get("data", {}))
                            return {"response": f"Here are your current holdings:\n\n{formatted}"}
                        else:
                            error_msg = result.get("error", "Unknown error")
                            return {"response": f"Failed to fetch holdings: {error_msg}"}

                    # If user asked about trend/analysis and no tool was called, force analyze_market
                    trend_keywords = ["trend", "analysis", "performance", "movement", "direction", "how is", "how are"]
                    if any(keyword in user_message for keyword in trend_keywords) and "tool_calls" not in message:
                        print("Detected trend/analysis query but no tool call - will search and analyze")
                        # This will be handled by the fallback code below that searches for instruments

                    # Try to extract get_market_quote call from code
                    match = re.search(r'get_market_quote\s*\(\s*({[^}]+})\s*\)', content, re.IGNORECASE)
                    if match:
                        try:
                            # Extract and execute
                            args_str = match.group(1).replace("'", '"')
                            args = json.loads(args_str)
                            result = await execute_tool("get_market_quote", {"securities": args}, access_token)
                            if result.get("success"):
                                formatted = format_market_quote_result(result.get("data", {}))
                                return {"response": f"I've fetched the current market data:\n\n{formatted}\n\nLet me know if you need any analysis of this data."}
                        except Exception as e:
                            print(f"Fallback execution failed: {e}")

                    # Fallback: If user asked about a stock/index by name and no tool was called,
                    # automatically search for it first, then fetch the quote
                    user_message = messages[-1].get("content", "").lower() if messages else ""
                    if any(keyword in user_message for keyword in ["nifty", "hdfc", "reliance", "tcs", "infy", "sensex", "bank nifty"]):
                        # Extract the instrument name
                        instrument_name = None
                        if "nifty" in user_message:
                            instrument_name = "NIFTY"
                            instrument_type = "INDEX"
                        elif "sensex" in user_message:
                            instrument_name = "SENSEX"
                            instrument_type = "INDEX"
                        elif "hdfc" in user_message:
                            instrument_name = "HDFC"
                            instrument_type = "EQUITY"
                        elif "reliance" in user_message:
                            instrument_name = "RELIANCE"
                            instrument_type = "EQUITY"

                        if instrument_name:
                            # First search for the instrument
                            search_result = await execute_tool(
                                "search_instruments",
                                {"query": instrument_name, "instrument_type": instrument_type, "limit": 1},
                                access_token
                            )

                            if search_result.get("success") and search_result.get("data", {}).get("instruments"):
                                instruments = search_result["data"]["instruments"]
                                if len(instruments) > 0:
                                    inst = instruments[0]
                                    security_id = inst.get("security_id")
                                    exchange_segment = inst.get("exchange_segment")

                                    # Debug logging if fields are missing
                                    if not security_id or not exchange_segment:
                                        print(f"[chat] Warning: Missing fields in search result for {instrument_name}")
                                        print(f"[chat] security_id: {security_id}, exchange_segment: {exchange_segment}")
                                        print(f"[chat] Instrument keys: {list(inst.keys())}")
                                        print(f"[chat] Full instrument data: {inst}")

                                    if security_id and exchange_segment:
                                        # Log which instrument is being used
                                        instrument_details = {
                                            "name": inst.get("display_name") or inst.get("symbol_name") or instrument_name,
                                            "security_id": security_id,
                                            "exchange_segment": exchange_segment,
                                            "instrument_type": inst.get("instrument_type", "N/A"),
                                            "symbol_name": inst.get("symbol_name", "N/A"),
                                            "underlying_symbol": inst.get("underlying_symbol", "N/A")
                                        }
                                        print(f"[chat] Using instrument for analysis: {json.dumps(instrument_details, indent=2)}")

                                        # Check if this is a trend/analysis query
                                        is_trend_query = any(keyword in user_message for keyword in ["trend", "analysis", "performance", "movement", "direction", "how is", "how are"])

                                        if is_trend_query:
                                            # Use analyze_market for trend analysis
                                            print(f"[chat] Calling analyze_market with security_id={security_id}, exchange_segment={exchange_segment}")
                                            analysis_result = await execute_tool(
                                                "analyze_market",
                                                {"security_id": security_id, "exchange_segment": exchange_segment, "days": 30},
                                                access_token
                                            )

                                            if analysis_result.get("success"):
                                                instrument_name_for_format = inst.get("display_name") or inst.get("symbol_name") or instrument_name
                                                data = analysis_result.get("data", {})

                                                # Add instrument details to response
                                                instrument_info = f"**Instrument Details:**\n- Name: {instrument_details['name']}\n- Security ID: {security_id}\n- Exchange: {exchange_segment}\n- Type: {instrument_details['instrument_type']}\n\n"

                                                # Format the analysis result
                                                if data.get("formatted_analysis"):
                                                    formatted = data["formatted_analysis"]
                                                elif data.get("metrics"):
                                                    metrics = data["metrics"]
                                                    trend = metrics.get("trend", {})
                                                    if trend:
                                                        formatted = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\n{metrics.get('trend_summary', '')}"
                                                    else:
                                                        formatted = f"Current Price: ₹{metrics.get('current_price', 'N/A')}\n\nHistorical data available but trend calculation failed."
                                                else:
                                                    formatted = json.dumps(data, indent=2)

                                                return {"response": f"{instrument_info}Here's the trend analysis for {instrument_name_for_format}:\n\n{formatted}"}
                                            else:
                                                error_msg = analysis_result.get("error", "Unknown error")
                                                return {"response": f"**Instrument Found:**\n- Name: {instrument_details['name']}\n- Security ID: {security_id}\n- Exchange: {exchange_segment}\n- Type: {instrument_details['instrument_type']}\n\n**Error:** Failed to analyze trend: {error_msg}"}
                                        else:
                                            # Regular price query - use get_market_quote
                                            print(f"[chat] Calling get_market_quote with securities={{'{exchange_segment}': [{security_id}]}}")
                                            quote_result = await execute_tool(
                                                "get_market_quote",
                                                {"securities": {exchange_segment: [security_id]}},
                                                access_token
                                            )

                                            if quote_result.get("success"):
                                                # Pass instrument name to formatting function for better symbol extraction
                                                instrument_name_for_format = inst.get("display_name") or inst.get("symbol_name") or instrument_name
                                                formatted = format_market_quote_result(quote_result.get("data", {}), instrument_name=instrument_name_for_format)

                                                # Add instrument details to response
                                                instrument_info = f"**Instrument Details:**\n- Name: {instrument_details['name']}\n- Security ID: {security_id}\n- Exchange: {exchange_segment}\n- Type: {instrument_details['instrument_type']}\n- Symbol: {instrument_details['symbol_name']}\n\n"
                                                return {"response": f"{instrument_info}Here's the current {instrument_name_for_format} data:\n\n{formatted}"}
                                            else:
                                                error_msg = quote_result.get("error", "Unknown error")
                                                symbol_name = inst.get("display_name") or inst.get("symbol_name") or instrument_name
                                                return {"response": f"**Instrument Found:**\n- Name: {symbol_name}\n- Security ID: {security_id}\n- Exchange: {exchange_segment}\n- Type: {instrument_details['instrument_type']}\n\n**Error:** Failed to fetch market data: {error_msg}"}
                                    else:
                                        return {"response": f"Found {instrument_name} but missing security_id or exchange_segment in search results."}
                                else:
                                    return {"response": f"Could not find {instrument_name} in the instrument database. Please check the spelling or try a different search term."}
                            else:
                                error_msg = search_result.get("error", "Unknown error")
                                # Add more context to error message
                                error_detail = search_result.get("data", {}).get("error_detail", "")
                                if error_detail:
                                    error_msg = f"{error_msg}. Details: {error_detail}"
                                print(f"[chat] Search failed for {instrument_name}: {error_msg}")
                                print(f"[chat] Search result: {search_result}")
                                return {"response": f"Failed to search for {instrument_name}: {error_msg}"}

                return {"response": content}
            return {"response": ""}
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"OpenAI-compatible API is not reachable at {OPENAI_API_BASE}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def generate_ollama_response_stream(prompt: str):
    """Generate streaming response from Ollama"""
    if OLLAMA_LIBRARY_AVAILABLE:
        # Use Ollama Python library if available
        try:
            client = AsyncClient(host=OLLAMA_BASE_URL)
            messages = [{'role': 'user', 'content': prompt}]

            async for chunk in await client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=True
            ):
                content = chunk.get('message', {}).get('content', '')
                if content:
                    yield f"data: {json.dumps({'content': content, 'done': False})}\n\n"

                if chunk.get('done', False):
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                    break
            return
        except Exception as e:
            error_msg = f"⚠️ Error: {str(e)}"
            if "Connection" in str(e) or "refused" in str(e).lower():
                error_msg = "⚠️ Ollama is not running. Please start Ollama: `ollama serve`"
            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
            return

    # Fallback to HTTP requests if library not available
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": True
            }

            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_msg = f"⚠️ Error: {error_text.decode()}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "response" in data:
                                yield f"data: {json.dumps({'content': data['response'], 'done': data.get('done', False)})}\n\n"
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue
    except httpx.ConnectError:
        error_msg = "⚠️ Ollama is not running. Please start Ollama: `ollama serve`"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"


async def generate_ollama_response(prompt: str):
    """Generate non-streaming response from Ollama"""
    if OLLAMA_LIBRARY_AVAILABLE:
        # Use Ollama Python library if available
        try:
            client = AsyncClient(host=OLLAMA_BASE_URL)
            messages = [{'role': 'user', 'content': prompt}]

            response = await client.chat(
                model=OLLAMA_MODEL,
                messages=messages,
                stream=False
            )

            content = response.get('message', {}).get('content', '')
            return {"response": content}
        except Exception as e:
            error_msg = str(e)
            if "Connection" in error_msg or "refused" in error_msg.lower():
                raise HTTPException(status_code=503, detail="Ollama is not running. Please start Ollama: ollama serve")
            raise HTTPException(status_code=500, detail=error_msg)

    # Fallback to HTTP requests if library not available
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            url = f"{OLLAMA_BASE_URL}/api/generate"
            payload = {
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            }

            response = await client.post(url, json=payload)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama is not running. Please start Ollama: ollama serve")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint"""
    try:
        # Build context-aware prompt
        context_parts = []
        if request.context:
            context_parts.append("Context from project files:")
            context_parts.extend(request.context[:3])  # Limit context

        prompt = f"""You are an AI coding assistant. Help the user with their coding questions.

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

Provide a helpful, concise response with code examples when relevant."""

        if USE_OLLAMA_ROUTER and OLLAMA_ROUTER_BASE:
            # Use Ollama Router native endpoint with X-Task header support
            response = await generate_ollama_router_response(prompt, task=request.task)
            return {"response": response.get("response", "")}
        elif USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            return {"response": response.get("response", "")}
        else:
            response = await generate_ollama_response(prompt)
            return {"response": response.get("response", "")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with optional trading support"""
    try:
        # Use provided token or fallback to environment variable
        access_token = get_access_token(request.access_token)
        # Determine if this is a trading request
        is_trading_request = access_token is not None or request.task == "trading"

        # Build context-aware prompt
        context_parts = []
        if request.context:
            context_parts.append("Context from project files:")
            context_parts.extend(request.context[:3])

        if is_trading_request:
            # Trading assistant prompt
            prompt = f"""You are an AI trading assistant with access to real-time market data and trading APIs via DhanHQ.

You can help users with:
- Market analysis and price quotes
- Portfolio positions and P&L analysis
- Trading strategies and insights
- Options chain analysis
- Historical data analysis
- Risk management advice

Common Security IDs:
- NIFTY 50: 99926000 (NSE_IDX)
- NIFTY Bank: 99926009 (NSE_IDX)
- HDFC Bank: 1333 (NSE_EQ)
- Reliance: 11536 (NSE_EQ)
- TCS: 11536 (NSE_EQ)

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

IMPORTANT: You have access to DhanHQ trading APIs through function calling. When users ask about prices, positions, or market data, you MUST use the available tools to fetch real-time information. Do NOT generate code examples - use the actual function calling tools."""
        else:
            # Coding assistant prompt
            prompt = f"""You are an AI coding assistant. Help the user with their coding questions.

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

Provide a helpful, concise response with code examples when relevant."""

        if USE_OLLAMA_ROUTER and OLLAMA_ROUTER_BASE:
            # Ollama Router native endpoint - use non-streaming and simulate streaming
            async def ollama_router_wrapper():
                try:
                    response = await generate_ollama_router_response(prompt, task=request.task)
                    content = response.get("response", "")
                    # Send content in chunks to simulate streaming
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"data: {json.dumps({'content': chunk, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'content': '', 'done': True})}\n\n"
                except Exception as e:
                    error_detail = str(e) if str(e) else repr(e)
                    if not error_detail:
                        error_detail = "Ollama Router error occurred. Please check if Ollama Router is running and configured correctly."
                    error_msg = f"⚠️ Error: {error_detail}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

            return StreamingResponse(
                ollama_router_wrapper(),
                media_type="text/event-stream"
            )
        elif USE_OPENAI_API and OPENAI_API_BASE:
            # OpenAI-compatible APIs with optional tool calling support
            # Use non-streaming and send as a single chunk for better reliability
            async def non_streaming_wrapper():
                try:
                    # Use tools if this is a trading request with access token
                    tools_to_use = None
                    if is_trading_request and request.access_token:
                        tools_to_use = DHANHQ_TOOLS

                    # Build messages with system prompt
                    messages_list = []
                    if is_trading_request:
                        messages_list.append({
                            "role": "system",
                            "content": """You are a trading assistant with access to real-time market data via DhanHQ APIs through function calling tools.

CRITICAL WORKFLOW:
1. When users ask about stocks, indices, or instruments by NAME (e.g., "NIFTY", "HDFC Bank", "RELIANCE"):
   - FIRST: Call search_instruments with the name to find security_id and exchange_segment
   - THEN: Use the returned security_id and exchange_segment for other operations (get_market_quote, get_historical_data, analyze_market, etc.)

2. When users ask about PRICES or CURRENT MARKET DATA:
   - Call search_instruments first to get security_id and exchange_segment
   - Then call get_market_quote with those values
   - Present the actual price data

3. When users ask about TRENDS, ANALYSIS, or HISTORICAL PERFORMANCE:
   - Call search_instruments first to get security_id and exchange_segment
   - Then call analyze_market OR get_historical_data to get trend information
   - analyze_market provides comprehensive analysis (current price + historical trend) using daily data
   - get_historical_data provides raw historical OHLCV data for custom analysis
   - For daily data: use interval="daily" with dates in YYYY-MM-DD format
   - For intraday data: use interval="1", "5", "15", "25", or "60" (minutes) with dates in YYYY-MM-DD HH:MM:SS format (market hours: 09:15:00 to 15:30:00)
   - Intraday data returns candle objects with timestamp, time, date, OHLC, volume, and open_interest (for F&O)
   - For indices (NIFTY, SENSEX), use exchange_segment="IDX_I" and instrument_type="INDEX"

4. When users ask about positions, holdings, or portfolio:
   - Use the available tools to fetch real data
   - DO NOT generate Python code or pseudo-code - use the actual function calling tools
   - DO NOT ask users for more details - use the tools with the information you have

5. Workflow examples:
   User: "What's the price of NIFTY?"
   Step 1: Call search_instruments(query="NIFTY", instrument_type="INDEX") or find_instrument(query="NIFTY", instrument_type="INDEX")
   Step 2: Extract security_id (should be 13 for NIFTY 50) and exchange_segment (should be "IDX_I") from the search results
   Step 3: Call get_market_quote with securities={"IDX_I": [13]} (using the actual security_id from step 2)
   Step 4: Format and provide the actual price from the response

   IMPORTANT: Always use the exact security_id and exchange_segment returned from search_instruments/find_instrument. Do not guess or use hardcoded values.

   User: "What is the SENSEX trend?"
   Step 1: Call search_instruments(query="SENSEX", instrument_type="INDEX")
   Step 2: Use the returned security_id and exchange_segment="IDX_I" to call analyze_market
   Step 3: Analyze the trend data and provide insights about direction (up/down/neutral) and percentage change

Available tools:
- search_instruments: Search for instruments by name/symbol (USE THIS FIRST when user mentions a stock/index by name)
- get_market_quote: Get current prices (requires security_id and exchange_segment from search_instruments)
- get_historical_data: Get price history for trend analysis (requires security_id, exchange_segment, instrument_type, from_date, to_date, interval)
  * For daily data: interval="daily", dates in YYYY-MM-DD format
  * For intraday data: interval="1", "5", "15", "25", or "60" (minutes), dates in YYYY-MM-DD HH:MM:SS format (09:15:00 to 15:30:00)
  * Returns OHLCV data: daily format has date/open/high/low/close/volume, intraday format adds timestamp/time/open_interest
- analyze_market: Comprehensive market analysis with trend (requires security_id and exchange_segment) - USE THIS FOR TREND QUERIES
- get_positions: Get user's open positions
- get_holdings: Get user's holdings
- get_fund_limits: Get balance and margin
- get_option_chain: Get options data (requires security_id and exchange_segment)

IMPORTANT:
- Always search for instruments first if the user mentions a stock/index by name
- For TREND queries, use analyze_market tool (it combines current price + historical data + trend analysis)
- For indices (NIFTY, SENSEX), the exchange_segment will be "IDX_I" and instrument_type should be "INDEX"
- Use the search results for all subsequent operations"""
                        })
                    messages_list.append({"role": "user", "content": request.message})

                    response = await generate_openai_response(
                        prompt=None,  # Not used when messages are provided
                        tools=tools_to_use,
                        messages=messages_list,
                        access_token=access_token if is_trading_request else None
                    )
                    content = response.get("response", "")
                    tool_calls = response.get("tool_calls", [])
                    reasoning = response.get("reasoning", "")

                    # Send tool calls metadata first (if any)
                    if tool_calls and len(tool_calls) > 0:
                        yield f"data: {json.dumps({'type': 'tool_calls', 'tool_calls': tool_calls, 'done': False})}\n\n"

                    # Send reasoning if available
                    if reasoning:
                        yield f"data: {json.dumps({'type': 'reasoning', 'content': reasoning, 'done': False})}\n\n"

                    # Send content in chunks to simulate streaming
                    chunk_size = 10
                    for i in range(0, len(content), chunk_size):
                        chunk = content[i:i + chunk_size]
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk, 'done': False})}\n\n"
                    yield f"data: {json.dumps({'type': 'content', 'content': '', 'done': True})}\n\n"
                except Exception as e:
                    error_detail = str(e) if str(e) else repr(e)
                    if not error_detail:
                        error_detail = "OpenAI-compatible API error occurred. Please check if the API is running and configured correctly."
                    error_msg = f"⚠️ Error: {error_detail}"
                    yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"

            return StreamingResponse(
                non_streaming_wrapper(),
                media_type="text/event-stream"
            )
        else:
            return StreamingResponse(
                generate_ollama_response_stream(prompt),
                media_type="text/event-stream"
            )
    except HTTPException as e:
        # Return HTTP exception as streaming error
        async def error_wrapper():
            error_detail = e.detail if e.detail else "HTTP error occurred"
            error_msg = f"⚠️ Error: {error_detail}"
            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
        return StreamingResponse(
            error_wrapper(),
            media_type="text/event-stream"
        )
    except Exception as e:
        # Return general exception as streaming error
        async def error_wrapper():
            error_detail = str(e) if str(e) else repr(e)
            if not error_detail:
                error_detail = "Unknown error occurred. Please check if Ollama is running or if the API is configured correctly."
            error_msg = f"⚠️ Error: {error_detail}"
            yield f"data: {json.dumps({'content': error_msg, 'done': True, 'error': True})}\n\n"
        return StreamingResponse(
            error_wrapper(),
            media_type="text/event-stream"
        )


@app.post("/api/generate/component")
async def generate_component(request: ComponentGenerateRequest):
    """Generate UI component from description"""
    try:
        prompt = f"""Generate a React component based on this description: {request.description}

Requirements:
- Use modern React with functional components and hooks
- Include TypeScript types
- Use Tailwind CSS for styling
- Make it responsive and accessible
- Include proper prop types
- Add comments for clarity

Return ONLY the component code, no explanations."""

        if USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            component_code = response.get("response", "")
        else:
            response = await generate_ollama_response(prompt)
            component_code = response.get("response", "")

        return {
            "component": component_code,
            "description": request.description,
            "framework": request.framework
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/generate/design-system")
async def generate_design_system(request: DesignSystemRequest):
    """Generate design system from description"""
    try:
        prompt = f"""Generate a design system configuration based on this description: {request.description}

Include:
- Color palette (primary, secondary, accent colors)
- Typography scale (font families, sizes, weights)
- Spacing system (margins, paddings)
- Border radius values
- Shadow definitions
- Animation/transition settings

Return a JSON object with all these properties. Use a dark theme with violet/blue accents as default."""

        if USE_OPENAI_API and OPENAI_API_BASE:
            response = await generate_openai_response(prompt)
            design_system = response.get("response", "")
        else:
            response = await generate_ollama_response(prompt)
            design_system = response.get("response", "")

        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            import re
            json_match = re.search(r'\{.*\}', design_system, re.DOTALL)
            if json_match:
                design_system = json.loads(json_match.group())
        except:
            pass

        return {
            "design_system": design_system,
            "description": request.description,
            "style": request.style
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Trading endpoints
@app.post("/api/trading/auth/token")
async def trading_auth_token(request: TradingAuthRequest):
    """Authenticate with access token directly"""
    if not request.token_id:  # Using token_id field for access_token
        raise HTTPException(status_code=400, detail="Access token is required")

    # Validate token by getting user profile
    result = trading_service.get_user_profile(request.token_id)
    if not result.get("success"):
        error_detail = result.get("error", "Invalid access token")
        # Log the error for debugging
        import logging
        logging.error(f"Token validation failed: {error_detail}")
        raise HTTPException(status_code=401, detail=error_detail)

    return {
        "success": True,
        "access_token": request.token_id,
        "data": result.get("data")
    }


@app.post("/api/trading/auth/pin")
async def trading_auth_pin(request: TradingAuthRequest):
    """Authenticate with PIN and TOTP"""
    if not request.pin or not request.totp:
        raise HTTPException(status_code=400, detail="PIN and TOTP are required")
    result = trading_service.authenticate_with_pin(request.pin, request.totp)
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Authentication failed"))
    return result


@app.post("/api/trading/auth/oauth")
async def trading_auth_oauth():
    """Generate OAuth consent URL"""
    result = trading_service.authenticate_oauth(
        trading_service.app_id or "",
        trading_service.app_secret or ""
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "OAuth initialization failed"))
    return result


@app.post("/api/trading/auth/consume")
async def trading_auth_consume(request: TradingAuthRequest):
    """Consume token ID from OAuth redirect"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Token ID is required")
    result = trading_service.consume_token_id(
        request.token_id,
        trading_service.app_id or "",
        trading_service.app_secret or ""
    )
    if not result.get("success"):
        raise HTTPException(status_code=401, detail=result.get("error", "Token consumption failed"))
    return result


@app.post("/api/trading/profile")
async def trading_profile(request: TradingAuthRequest):
    """Get user profile"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_user_profile(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get profile"))
    return result


@app.post("/api/trading/orders/place")
async def place_order(request: PlaceOrderRequest):
    """Place a trading order"""
    result = trading_service.place_order(request.access_token, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to place order"))
    return result


@app.post("/api/trading/orders")
async def get_orders(request: TradingAuthRequest):
    """Get all orders"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_orders(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get orders"))
    return result


@app.get("/api/trading/orders/{order_id}")
async def get_order(order_id: str, access_token: str):
    """Get order by ID"""
    result = trading_service.get_order_by_id(access_token, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get order"))
    return result


@app.post("/api/trading/orders/{order_id}/cancel")
async def cancel_order(order_id: str, request: TradingAuthRequest):
    """Cancel an order"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.cancel_order(request.token_id, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to cancel order"))
    return result


@app.post("/api/trading/orders/{order_id}/modify")
async def modify_order(order_id: str, request: ModifyOrderRequest):
    """Modify an order"""
    result = trading_service.modify_order(request.access_token, order_id, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to modify order"))
    return result


@app.post("/api/trading/positions")
async def get_positions(request: TradingAuthRequest):
    """Get current positions"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_positions(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get positions"))
    return result


@app.post("/api/trading/holdings")
async def get_holdings(request: TradingAuthRequest):
    """Get current holdings"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_holdings(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get holdings"))
    return result


@app.post("/api/trading/funds")
async def get_funds(request: TradingAuthRequest):
    """Get fund limits and margin details"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_fund_limits(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get funds"))
    return result


@app.post("/api/trading/market/quote")
async def get_market_quote(request: MarketQuoteRequest):
    """Get market quote data"""
    # Use provided token or fallback to environment variable
    access_token = get_access_token(request.access_token)
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token required. Provide access_token in request or set DHAN_ACCESS_TOKEN environment variable.")

    result = trading_service.get_market_quote(access_token, request.securities)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get market quote"))
    return result


@app.post("/api/trading/market/option-chain")
async def get_option_chain(request: OptionChainRequest):
    """Get option chain data"""
    result = trading_service.get_option_chain(
        request.access_token,
        request.under_security_id,
        request.under_exchange_segment,
        request.expiry
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get option chain"))
    return result


@app.post("/api/trading/market/historical")
async def get_historical_data(request: HistoricalDataRequest):
    """
    Get historical data (daily or intraday minute data)

    Per official DhanHQ example:
    - Uses DhanContext for initialization
    - Accepts security_id as string or int (converts to string internally)
    - Supports both daily and intraday minute data
    - Date format: "YYYY-MM-DD"

    Example request:
    {
        "access_token": "your_token",
        "security_id": "1333",  # or 1333 (will be converted to string)
        "exchange_segment": "NSE_EQ",
        "instrument_type": "EQUITY",
        "from_date": "2023-01-01",
        "to_date": "2023-01-31",
        "interval": "daily"  # or "intraday" or "minute"
    }
    """
    # Use provided token or fallback to environment variable
    access_token = get_access_token(request.access_token)
    if not access_token:
        raise HTTPException(status_code=400, detail="Access token required. Provide access_token in request or set DHAN_ACCESS_TOKEN environment variable.")

    # Convert security_id to int for the method (it will convert to string internally)
    security_id = int(request.security_id) if isinstance(request.security_id, str) else request.security_id

    result = trading_service.get_historical_data(
        access_token,
        security_id,
        request.exchange_segment,
        request.instrument_type,
        request.from_date,
        request.to_date,
        request.interval
    )
    if not result.get("success"):
        # Return the error with proper structure, including error code if available
        error_detail = result.get("error", "Failed to get historical data")
        error_code = result.get("error_code")
        if error_code:
            error_detail = f"[{error_code}] {error_detail}"
        raise HTTPException(status_code=500, detail=error_detail)
    return result


@app.post("/api/trading/securities")
async def get_securities(request: TradingAuthRequest):
    """Get security/instrument list"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_security_list(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get securities"))
    return result


@app.post("/api/trading/instruments/csv")
async def get_instrument_list_csv(request: InstrumentListCSVRequest):
    """Get instrument list from CSV endpoints (compact or detailed) - checks database first"""
    if request.format_type not in ["compact", "detailed"]:
        raise HTTPException(status_code=400, detail="format_type must be 'compact' or 'detailed'")

    # Try database first (with timeout protection)
    try:
        instruments = await asyncio.wait_for(
            db.get_instruments(request.format_type),
            timeout=5.0  # 5 second timeout for database query
        )
        if instruments and len(instruments) > 0:
            return {
                "success": True,
                "data": {
                    "instruments": instruments,
                    "count": len(instruments),
                    "format": request.format_type,
                    "source": "database"
                }
            }
    except asyncio.TimeoutError:
        print(f"Database query timeout for instruments, falling back to CSV API")
    except Exception as e:
        print(f"Database error for instruments: {e}, falling back to CSV API")

    # Fallback to CSV API if not in database or database query fails
    result = trading_service.get_instrument_list_csv(request.format_type)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get instrument list"))
    return result


@app.post("/api/trading/instruments/sync")
async def sync_instruments(background_tasks: BackgroundTasks, format_type: str = "detailed"):
    """Manually trigger instrument sync from CSV to database"""
    if format_type not in ["compact", "detailed"]:
        raise HTTPException(status_code=400, detail="format_type must be 'compact' or 'detailed'")

    # Run sync in background
    async def sync_task():
        result = await trading_service.sync_instruments_to_db(db, format_type)
        if result.get("success"):
            print(f"Instruments synced: {result['data']['synced_count']} instruments")
        else:
            print(f"Sync failed: {result.get('error')}")

    background_tasks.add_task(sync_task)

    return {
        "success": True,
        "message": "Instrument sync started in background",
        "format": format_type
    }


@app.get("/api/trading/instruments/metadata")
async def get_instruments_metadata():
    """Get instruments metadata (last update time, count, etc.)"""
    metadata = await db.get_instruments_metadata()
    if not metadata:
        return {
            "success": False,
            "message": "No instruments metadata found"
        }
    return {
        "success": True,
        "data": metadata
    }


@app.post("/api/trading/instruments/segmentwise")
async def get_instrument_list_segmentwise(request: InstrumentListSegmentwiseRequest):
    """Get detailed instrument list for a particular exchange and segment (no authentication required)"""
    if not request.exchange_segment:
        raise HTTPException(status_code=400, detail="Exchange segment is required")
    try:
        result = await trading_service.get_instrument_list_segmentwise(request.exchange_segment, request.access_token)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "Failed to get instrument list"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        error_detail = str(e) if str(e) else repr(e)
        print(f"Error in segmentwise endpoint: {error_detail}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get instrument list: {error_detail}. Check backend logs for details."
        )


@app.post("/api/trading/expiry-list")
async def get_expiry_list(request: ExpiryListRequest):
    """Get expiry list for underlying"""
    result = trading_service.get_expiry_list(
        request.access_token,
        request.under_security_id,
        request.under_exchange_segment
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get expiry list"))
    return result


@app.post("/api/trading/trades")
async def get_trades(request: TradingAuthRequest):
    """Get all trades executed today"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_trades(request.token_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trades"))
    return result


@app.post("/api/trading/trades/{order_id}")
async def get_trade_by_order_id(order_id: str, request: TradingAuthRequest):
    """Get trades by order ID"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")
    result = trading_service.get_trade_by_order_id(request.token_id, order_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trade"))
    return result


@app.post("/api/trading/trades/history")
async def get_trade_history(request: TradeHistoryRequest):
    """Get trade history for date range"""
    result = trading_service.get_trade_history(
        request.access_token,
        request.from_date,
        request.to_date,
        request.page_number
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get trade history"))
    return result


@app.post("/api/trading/margin/calculator")
async def calculate_margin(request: MarginCalculatorRequest):
    """Calculate margin for an order"""
    result = trading_service.calculate_margin(request.access_token, request.dict())
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to calculate margin"))
    return result


@app.post("/api/trading/killswitch")
async def manage_kill_switch(request: KillSwitchRequest):
    """Get or manage kill switch status"""
    if not request.token_id:
        raise HTTPException(status_code=400, detail="Access token is required")

    if request.status:
        # Manage kill switch
        result = trading_service.manage_kill_switch(request.token_id, request.status)
    else:
        # Get status
        result = trading_service.get_kill_switch_status(request.token_id)

    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to manage kill switch"))
    return result


@app.post("/api/trading/ledger")
async def get_ledger(request: LedgerRequest):
    """Get ledger report"""
    result = trading_service.get_ledger(
        request.access_token,
        request.from_date,
        request.to_date
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Failed to get ledger"))
    return result


# WebSocket connections manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.market_feeds: Dict[str, Any] = {}
        self.order_updates: Dict[str, Any] = {}
        self.full_depths: Dict[str, Any] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"Error sending message: {e}")
            self.disconnect(websocket)

manager = ConnectionManager()


@app.websocket("/ws/trading/market-feed/{access_token}")
async def market_feed_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for real-time market feed using DhanHQ MarketFeed"""
    await manager.connect(websocket)
    market_feed = None
    feed_thread = None

    try:
        # Receive subscription request
        data = await websocket.receive_json()

        # Support both formats:
        # 1. New format (per DhanHQ docs): {RequestCode, InstrumentCount, InstrumentList: [{ExchangeSegment, SecurityId}]}
        # 2. Legacy format: {instruments: [[exchange_code, security_id, feed_code]], version}

        # Feed Request Codes (per DhanHQ Annexure):
        # 15 = Subscribe - Ticker Packet
        # 17 = Subscribe - Quote Packet
        # 21 = Subscribe - Full Packet
        request_code = data.get("RequestCode", 17)  # Default to 17 (Quote Packet subscription)
        instrument_list = data.get("InstrumentList", [])
        instruments = data.get("instruments", [])
        version = data.get("version", "v2")  # Default to v2 as per DhanHQ WebSocket API

        # Convert to standard format
        instrument_tuples = []

        # Handle new format: InstrumentList with ExchangeSegment and SecurityId
        if instrument_list:
            # Map ExchangeSegment to exchange code (per DhanHQ Annexure)
            # IDX_I = Index (enum 0) - for indices like NIFTY, SENSEX
            exchange_map = {
                "IDX_I": 0,  # Index segment (for indices)
                "NSE_EQ": 1, "NSE_FNO": 1, "NSE_CUR": 1, "NSE_COM": 1,
                "BSE_EQ": 2, "BSE_FNO": 2, "BSE_CUR": 2, "BSE_COM": 2,
                "MCX_COM": 3, "NCDEX_COM": 4
            }

            # Map RequestCode (WebSocket API) to feed_request_code (MarketFeed SDK)
            # WebSocket RequestCode → MarketFeed SDK feed_request_code:
            # 15 = Subscribe - Ticker Packet → feed_code 1
            # 17 = Subscribe - Quote Packet → feed_code 2
            # 21 = Subscribe - Full Packet → feed_code 3
            # Note: MarketFeed SDK uses feed_request_code (1,2,3) not RequestCode (15,17,21)
            feed_code_map = {
                15: 1,  # Ticker Packet
                17: 2,  # Quote Packet
                21: 3,  # Full Packet
            }
            feed_code = feed_code_map.get(request_code, 2)  # Default to Quote Packet (feed_code 2)

            for inst in instrument_list:
                exchange_segment = inst.get("ExchangeSegment", "")
                security_id_str = inst.get("SecurityId", "")

                if not exchange_segment or not security_id_str:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Invalid instrument format: {inst}. Expected {{ExchangeSegment, SecurityId}}"
                    }, websocket)
                    return

                # Get exchange code from segment
                # Direct lookup first (most efficient)
                exchange_code = exchange_map.get(exchange_segment)

                if exchange_code is None:
                    # Try to extract from segment name for fallback
                    if exchange_segment == "IDX_I":
                        exchange_code = 0  # Index segment (enum 0 per Annexure)
                    elif "NSE" in exchange_segment:
                        exchange_code = 1
                    elif "BSE" in exchange_segment:
                        exchange_code = 2
                    elif "MCX" in exchange_segment:
                        exchange_code = 3
                    elif "NCDEX" in exchange_segment:
                        exchange_code = 4
                    else:
                        exchange_code = 1  # Default to NSE

                security_id = int(security_id_str)
                instrument_tuples.append((exchange_code, security_id, feed_code))

        # Handle legacy format: instruments array
        elif instruments:
            for inst in instruments:
                if isinstance(inst, (list, tuple)) and len(inst) >= 2:
                    exchange_code = int(inst[0])
                    security_id = int(inst[1]) if isinstance(inst[1], (int, str)) else int(str(inst[1]))
                    feed_code = int(inst[2]) if len(inst) >= 3 else 2  # Default to Quote mode
                    instrument_tuples.append((exchange_code, security_id, feed_code))
                elif isinstance(inst, dict):
                    # Support dict format too
                    exchange_segment = inst.get("ExchangeSegment", inst.get("exchangeSegment", ""))
                    security_id_str = inst.get("SecurityId", inst.get("securityId", ""))
                    if exchange_segment and security_id_str:
                        # Map exchange segment to code
                        exchange_map = {
                            "NSE_EQ": 1, "NSE_FNO": 1, "BSE_EQ": 2, "BSE_FNO": 2, "MCX_COM": 3
                        }
                        exchange_code = exchange_map.get(exchange_segment, 1)
                        security_id = int(security_id_str)
                        feed_code = inst.get("feedCode", inst.get("FeedCode", 2))
                        instrument_tuples.append((exchange_code, security_id, feed_code))

        if not instrument_tuples:
            await manager.send_personal_message({
                "type": "error",
                "message": "No valid instruments provided for subscription"
            }, websocket)
            return

        print(f"Subscribing to {len(instrument_tuples)} instruments: {instrument_tuples}")

        # Create market feed instance
        try:
            market_feed = trading_service.create_market_feed(access_token, instrument_tuples, version)
            manager.market_feeds[access_token] = market_feed

            # Send connection success message
            await manager.send_personal_message({
                "type": "connected",
                "message": "Market feed connected successfully",
                "instruments_count": len(instrument_tuples)
            }, websocket)

            # Initialize and authorize market feed connection
            # MarketFeed requires async initialization
            async def initialize_market_feed():
                try:
                    # Check what instruments are actually in the feed
                    if hasattr(market_feed, 'instruments'):
                        print(f"DhanFeed instruments before subscription: {market_feed.instruments}")

                    # Authorize the connection (async method)
                    print("Calling authorize()...")
                    await market_feed.authorize()
                    print("Authorization successful")

                    # Connect to WebSocket (async method)
                    print("Calling connect()...")
                    # Add timeout for connection (30 seconds)
                    try:
                        await asyncio.wait_for(market_feed.connect(), timeout=30.0)
                        print("Connection successful")
                    except asyncio.TimeoutError:
                        print("Connection timeout - DhanHQ WebSocket may be unreachable")
                        raise Exception("Connection timeout: DhanHQ WebSocket server may be unreachable or market is closed")
                    except Exception as e:
                        # Check if this is a rate limit error (HTTP 429)
                        error_str = str(e)
                        if "429" in error_str or "rate limit" in error_str.lower() or "InvalidStatus" in str(type(e).__name__):
                            # Handle rate limiting gracefully
                            print(f"Rate limit detected (HTTP 429): {e}")
                            print("Market feed connection rate limited. Will continue without real-time feed.")
                            await manager.send_personal_message({
                                "type": "warning",
                                "message": "Market feed connection rate limited by DhanHQ (HTTP 429). Real-time market data is temporarily unavailable. Please wait a few minutes and try again. You can still use the REST API endpoints for market data."
                            }, websocket)
                            # Return None to indicate market feed is not available, but don't crash
                            return None
                        else:
                            print(f"Connection error: {e}")
                            raise

                    # Subscribe to instruments (async method)
                    print("Calling subscribe_instruments()...")
                    await market_feed.subscribe_instruments()
                    print("Subscription successful")
                    return True  # Success
                except Exception as e:
                    # Check if this is a rate limit error (HTTP 429)
                    error_str = str(e)
                    if "429" in error_str or "rate limit" in error_str.lower() or "InvalidStatus" in str(type(e).__name__):
                        # Handle rate limiting gracefully
                        print(f"Rate limit detected (HTTP 429): {e}")
                        print("Market feed connection rate limited. Will continue without real-time feed.")
                        await manager.send_personal_message({
                            "type": "warning",
                            "message": "Market feed connection rate limited by DhanHQ (HTTP 429). Real-time market data is temporarily unavailable. Please wait a few minutes and try again. You can still use the REST API endpoints for market data."
                        }, websocket)
                        # Return None to indicate market feed is not available, but don't crash
                        return None
                    else:
                        print(f"Market feed initialization error: {e}")
                        import traceback
                        print(f"Traceback: {traceback.format_exc()}")
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"Failed to initialize market feed: {str(e)}"
                        }, websocket)
                        # For non-rate-limit errors, we can still continue without market feed
                        # Don't raise - allow WebSocket to stay connected
                        print("Continuing without market feed due to initialization error")
                        return None

            # Initialize market feed
            market_feed_initialized = await initialize_market_feed()

            # Only start market feed thread if initialization was successful
            if market_feed_initialized is None:
                print("Market feed not available. WebSocket will stay connected but no real-time data will be sent.")
                # Keep WebSocket alive but don't start market feed thread
                # Send periodic keepalive messages
                async def keepalive_loop():
                    while True:
                        await asyncio.sleep(30)
                        try:
                            await manager.send_personal_message({
                                "type": "keepalive",
                                "message": "Connection alive. Market feed unavailable due to rate limiting."
                            }, websocket)
                        except:
                            break

                # Start keepalive in background
                asyncio.create_task(keepalive_loop())

                # Wait for WebSocket disconnect
                try:
                    while True:
                        await websocket.receive_text()
                except:
                    pass
                return

            # Start market feed in background thread
            # MarketFeed.run_forever() is a blocking call that runs the event loop
            # We need to create a new event loop in the thread to avoid "event loop is already running" error
            def run_market_feed():
                try:
                    # Create a new event loop for this thread
                    # This avoids conflict with the existing asyncio event loop in FastAPI
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    # Run the market feed event loop (blocking)
                    market_feed.run_forever()
                except Exception as e:
                    print(f"Market feed error: {e}")
                finally:
                    # Clean up the event loop
                    try:
                        loop.close()
                    except:
                        pass

            feed_thread = threading.Thread(target=run_market_feed, daemon=True)
            feed_thread.start()

            # Wait a bit for connection to establish and data to start flowing
            await asyncio.sleep(2)

            # Send data to client as it arrives
            # Safety check: ensure market_feed is available
            if market_feed is None:
                print("Market feed not available, cannot send data")
                return

            no_data_count = 0  # Track consecutive empty responses
            last_data_time = None  # Track when we last received data
            packet_count = 0  # Track total packets received
            while True:
                try:
                    # get_data() returns data from the market feed queue
                    # Returns None/empty when no new data is available (e.g., market closed)
                    response = market_feed.get_data()

                    # Log all responses (including None) for debugging
                    if response:
                        packet_count += 1
                        print(f"[Market Feed] Packet #{packet_count} received: type={type(response).__name__}, keys={list(response.keys()) if isinstance(response, dict) else 'N/A'}")
                        print(f"[Market Feed] Raw response data: {response}")
                    else:
                        # Log when no data is received (helps debug market closed scenario)
                        if no_data_count == 0 or no_data_count % 100 == 0:  # Log every 100 empty responses (5 seconds)
                            print(f"[Market Feed] No data received (empty response #{no_data_count + 1})")

                    if response:
                        # Reset counters when we receive data
                        no_data_count = 0
                        last_data_time = datetime.now()

                        # MarketFeed returns data in various formats - normalize it
                        # It could be a dict, list, or nested structure
                        processed_data = response

                        # If it's a dict with nested data, extract it
                        if isinstance(response, dict):
                            # Check for common MarketFeed response structures
                            # MarketFeed may return data nested by exchange segment:
                            # { "IDX_I": { "13": {...}, "51": {...} } }
                            # or { "data": { "IDX_I": { "13": {...} } } }
                            if 'data' in response:
                                data_content = response['data']
                                # Check if data is nested by exchange segment (like IDX_I)
                                if isinstance(data_content, dict) and 'IDX_I' in data_content:
                                    # Flatten IDX_I data - convert to list of instruments
                                    idx_data = data_content['IDX_I']
                                    if isinstance(idx_data, dict):
                                        processed_data = [
                                            {**value, 'security_id': str(key), 'securityId': str(key)}
                                            for key, value in idx_data.items()
                                        ]
                                    else:
                                        processed_data = data_content
                                else:
                                    processed_data = data_content
                            elif 'instruments' in response:
                                processed_data = response['instruments']
                            elif 'quote' in response:
                                processed_data = response['quote']
                            elif 'ticker' in response:
                                processed_data = response['ticker']
                            elif 'IDX_I' in response:
                                # Direct IDX_I key - flatten it
                                idx_data = response['IDX_I']
                                if isinstance(idx_data, dict):
                                    processed_data = [
                                        {**value, 'security_id': str(key), 'securityId': str(key)}
                                        for key, value in idx_data.items()
                                    ]
                                else:
                                    processed_data = response
                            else:
                                processed_data = response

                        # Ensure security_id is a string for consistent matching
                        # MarketFeed returns data in various formats - normalize all possible structures
                        def normalize_security_id(data):
                            """Recursively normalize security_id fields to strings"""
                            if isinstance(data, dict):
                                # Normalize security_id field in dict
                                for key in ['security_id', 'securityId', 'SECURITY_ID', 'SecurityId', 'Security_ID', 'id']:
                                    if key in data:
                                        data[key] = str(data[key])
                                # Recursively process nested dicts
                                for value in data.values():
                                    if isinstance(value, (dict, list)):
                                        normalize_security_id(value)
                            elif isinstance(data, list):
                                # Process each item in list
                                for item in data:
                                    normalize_security_id(item)

                        normalize_security_id(processed_data)

                        # Debug logging for index instruments
                        if isinstance(processed_data, dict):
                            security_id_val = (processed_data.get('security_id') or
                                              processed_data.get('securityId') or
                                              processed_data.get('SECURITY_ID'))
                            if security_id_val in ['13', '51', 13, 51]:
                                print(f"Index instrument data received: security_id={security_id_val}, data={processed_data}")

                        # Log processed data before sending
                        print(f"[Market Feed] Sending processed data to frontend: type={type(processed_data).__name__}")
                        if isinstance(processed_data, dict):
                            print(f"[Market Feed] Processed data keys: {list(processed_data.keys())}")
                        elif isinstance(processed_data, list):
                            print(f"[Market Feed] Processed data: {len(processed_data)} items")
                            if len(processed_data) > 0:
                                print(f"[Market Feed] First item keys: {list(processed_data[0].keys()) if isinstance(processed_data[0], dict) else 'N/A'}")

                        # Process and send data to client
                        await manager.send_personal_message({
                            "type": "market_feed",
                            "data": processed_data
                        }, websocket)
                        print(f"[Market Feed] Data sent to frontend successfully")
                    else:
                        # No data received (market might be closed or no updates)
                        no_data_count += 1

                        # After 20 consecutive empty responses (1 second), reduce polling frequency
                        # and notify frontend if this is the first time we detect no data
                        if no_data_count == 20:
                            # Send a status update to frontend that we're not receiving data
                            # This could indicate market is closed or connection issue
                            await manager.send_personal_message({
                                "type": "market_status",
                                "status": "no_data",
                                "message": "No market data updates received. Market may be closed."
                            }, websocket)
                            print("No market data received for 1 second - market may be closed")

                        # Reduce polling frequency when no data (every 1 second instead of 50ms)
                        # This reduces CPU usage when market is closed
                        if no_data_count > 20:
                            await asyncio.sleep(1.0)  # Poll every 1 second when no data
                            continue

                    # Normal polling interval when data is flowing
                    await asyncio.sleep(0.05)  # Small delay to prevent CPU spinning
                except Exception as e:
                    print(f"Error processing market feed data: {e}")
                    await manager.send_personal_message({
                        "type": "error",
                        "message": str(e)
                    }, websocket)
                    break

        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Market Feed not available: {str(e)}"
            }, websocket)
        except Exception as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Failed to create market feed: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        pass  # Client disconnected
    except Exception as e:
        await manager.send_personal_message({
            "type": "error",
            "message": f"WebSocket error: {str(e)}"
        }, websocket)
    finally:
        # Cleanup
        manager.disconnect(websocket)
        if market_feed and access_token in manager.market_feeds:
            try:
                # Disconnect the market feed (disconnect is async, close_connection is sync)
                if hasattr(market_feed, 'disconnect'):
                    try:
                        await market_feed.disconnect()
                    except Exception as disconnect_err:
                        print(f"Error awaiting disconnect: {disconnect_err}")
                        # Fallback to close_connection if disconnect fails
                        if hasattr(market_feed, 'close_connection'):
                            market_feed.close_connection()
                elif hasattr(market_feed, 'close_connection'):
                    market_feed.close_connection()
            except Exception as e:
                print(f"Error disconnecting market feed: {e}")
            finally:
                del manager.market_feeds[access_token]


@app.websocket("/ws/trading/order-updates/{access_token}")
async def order_updates_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for real-time order updates"""
    await manager.connect(websocket)
    try:
        # Create order update instance
        try:
            order_update = trading_service.create_order_update(access_token)
            manager.order_updates[access_token] = order_update

            # Callback for order updates
            def on_order_update(order_data: dict):
                asyncio.create_task(manager.send_personal_message({
                    "type": "order_update",
                    "data": order_data
                }, websocket))

            order_update.on_update = on_order_update

            # Start order update in background thread
            def run_order_update():
                while True:
                    try:
                        order_update.connect_to_dhan_websocket_sync()
                    except Exception as e:
                        print(f"Order update error: {e}")
                        import time
                        time.sleep(5)

            update_thread = threading.Thread(target=run_order_update, daemon=True)
            update_thread.start()

            # Keep connection alive
            while True:
                try:
                    await websocket.receive_text()
                except WebSocketDisconnect:
                    break
        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Order Updates not available: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if access_token in manager.order_updates:
            del manager.order_updates[access_token]


@app.websocket("/ws/trading/full-depth/{access_token}")
async def full_depth_websocket(websocket: WebSocket, access_token: str):
    """WebSocket endpoint for 20-level market depth"""
    await manager.connect(websocket)
    try:
        # Receive subscription request
        data = await websocket.receive_json()
        instruments = data.get("instruments", [])

        # Create full depth instance
        try:
            full_depth = trading_service.create_full_depth(access_token, instruments)
            manager.full_depths[access_token] = full_depth

            # Start full depth in background thread
            def run_full_depth():
                try:
                    full_depth.run_forever()
                except Exception as e:
                    print(f"Full depth error: {e}")

            depth_thread = threading.Thread(target=run_full_depth, daemon=True)
            depth_thread.start()

            # Send data to client
            while True:
                try:
                    response = full_depth.get_data()
                    if response:
                        await manager.send_personal_message({
                            "type": "full_depth",
                            "data": response
                        }, websocket)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    await manager.send_personal_message({
                        "type": "error",
                        "message": str(e)
                    }, websocket)
                    break
        except (ImportError, AttributeError) as e:
            await manager.send_personal_message({
                "type": "error",
                "message": f"Full Depth not available: {str(e)}"
            }, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        if access_token in manager.full_depths:
            try:
                if hasattr(manager.full_depths[access_token], 'disconnect'):
                    manager.full_depths[access_token].disconnect()
            except:
                pass
            del manager.full_depths[access_token]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

