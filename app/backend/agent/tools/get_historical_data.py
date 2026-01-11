"""
Get Historical Data Tool

Fetches historical price data for technical analysis and trend calculation.
"""

from typing import Dict, Any, Optional
try:
    from agent.tools.base import Tool
except ImportError:
    from app.agent.tools.base import Tool
import sys
import os
# Add parent directory to path for imports
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
from trading import trading_service


class GetHistoricalDataTool(Tool):
    """Get historical price data (daily or intraday minute data) for technical analysis"""

    name = "get_historical_data"
    description = "Get historical price data (daily or intraday minute data) for technical analysis, backtesting, or trend analysis. Returns OHLCV data for the specified date range. For intraday data, supports intervals of 1, 5, 15, 25, or 60 minutes. Intraday data includes timestamps and can be used for detailed minute-by-minute analysis. Daily data provides end-of-day OHLCV values."

    input_schema = {
        "type": "object",
        "properties": {
            "security_id": {
                "type": "integer",
                "description": "Security ID (e.g., 1333 for HDFC Bank, 13 for NIFTY 50)"
            },
            "exchange_segment": {
                "type": "string",
                "description": "Exchange segment where the security is traded (use IDX_I for indices like NIFTY, SENSEX)",
                "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "MCX_COM", "NCDEX_COM", "IDX_I"]
            },
            "instrument_type": {
                "type": "string",
                "description": "Type of instrument (use INDEX for indices like NIFTY, SENSEX)",
                "enum": ["EQUITY", "FUTURES", "OPTIONS", "INDEX"]
            },
            "from_date": {
                "type": "string",
                "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01') for daily data, or YYYY-MM-DD HH:MM:SS format (e.g., '2024-01-01 09:15:00') for intraday data. For intraday, use market hours (09:15:00 to 15:30:00)."
            },
            "to_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (e.g., '2024-01-31') for daily data, or YYYY-MM-DD HH:MM:SS format (e.g., '2024-01-31 15:30:00') for intraday data. For intraday, use market hours (09:15:00 to 15:30:00)."
            },
            "interval": {
                "type": "string",
                "description": "Data interval - 'daily' for daily candles, or numeric string ('1', '5', '15', '25', '60') for intraday minute data. For intraday, intervals are in minutes: 1, 5, 15, 25, or 60 minutes.",
                "enum": ["daily", "1", "5", "15", "25", "60", "intraday", "minute"],
                "default": "daily"
            }
        },
        "required": ["security_id", "exchange_segment", "instrument_type", "from_date", "to_date"]
    }

    output_schema = {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "description": "Historical OHLCV data. For daily data: array of objects with date, open, high, low, close, volume. For intraday data: array of candle objects with timestamp (Unix epoch), time (ISO format), date (ISO format), open, high, low, close, volume, and open_interest (for F&O).",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Date in ISO format or YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Time in ISO format (for intraday data)"},
                        "timestamp": {"type": "integer", "description": "Unix epoch timestamp (for intraday data)"},
                        "open": {"type": "number", "description": "Open price"},
                        "high": {"type": "number", "description": "High price"},
                        "low": {"type": "number", "description": "Low price"},
                        "close": {"type": "number", "description": "Close price"},
                        "volume": {"type": "number", "description": "Volume traded"},
                        "open_interest": {"type": "number", "description": "Open interest (for Futures & Options, intraday data only)"}
                    }
                }
            },
            "count": {"type": "integer", "description": "Number of data points returned"}
        }
    }

    safety = {
        "read_only": True,
        "requires_confirmation": False
    }

    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute historical data fetch"""
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}

        if not access_token:
            return {"success": False, "error": "Access token required"}

        security_id = kwargs["security_id"]
        exchange_segment = kwargs["exchange_segment"]
        instrument_type = kwargs["instrument_type"]
        from_date = kwargs["from_date"]
        to_date = kwargs["to_date"]
        interval = kwargs.get("interval", "daily")

        result = trading_service.get_historical_data(
            access_token,
            security_id,
            exchange_segment,
            instrument_type,
            from_date,
            to_date,
            interval
        )

        if result.get("success"):
            data = result.get("data", [])
            if not isinstance(data, list):
                data = []

            return {
                "success": True,
                "data": data,
                "count": len(data)
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to fetch historical data")}

