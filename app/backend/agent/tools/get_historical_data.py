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
    description = "Get historical price data (daily or intraday minute data) for technical analysis, backtesting, or trend analysis. Returns OHLCV data for the specified date range."

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
                "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01')"
            },
            "to_date": {
                "type": "string",
                "description": "End date in YYYY-MM-DD format (e.g., '2024-01-31')"
            },
            "interval": {
                "type": "string",
                "description": "Data interval - 'daily' for daily candles, 'intraday' or 'minute' for minute-by-minute data",
                "enum": ["daily", "intraday", "minute"],
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
                "description": "Historical OHLCV data",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "open": {"type": "number"},
                        "high": {"type": "number"},
                        "low": {"type": "number"},
                        "close": {"type": "number"},
                        "volume": {"type": "number"}
                    }
                }
            },
            "count": {"type": "integer"}
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

