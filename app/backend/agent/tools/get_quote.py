"""
Get Market Quote Tool

Fetches real-time market quotes (OHLC data) for securities.
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


class GetQuoteTool(Tool):
    """Get real-time market quote (OHLC data) for securities"""

    name = "get_quote"
    description = "Get real-time market quote (OHLC data) for securities. Returns current price, open, high, low, close, volume, and other market data. Use this to check current prices and market status."

    input_schema = {
        "type": "object",
        "properties": {
            "securities": {
                "type": "object",
                "description": "Dictionary mapping exchange segments to list of security IDs. Example: {'NSE_EQ': [1333, 11536]} for HDFC Bank and Reliance, or {'IDX_I': [13]} for NIFTY 50",
                "additionalProperties": {
                    "type": "array",
                    "items": {"type": "integer"}
                }
            }
        },
        "required": ["securities"]
    }

    output_schema = {
        "type": "object",
        "properties": {
            "quotes": {
                "type": "array",
                "description": "List of market quotes",
                "items": {
                    "type": "object",
                    "properties": {
                        "security_id": {"type": "integer"},
                        "exchange_segment": {"type": "string"},
                        "ltp": {"type": "number"},
                        "open": {"type": "number"},
                        "high": {"type": "number"},
                        "low": {"type": "number"},
                        "close": {"type": "number"},
                        "volume": {"type": "number"}
                    }
                }
            }
        }
    }

    safety = {
        "read_only": True,
        "requires_confirmation": False
    }

    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute market quote fetch"""
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}

        if not access_token:
            return {"success": False, "error": "Access token required"}

        securities = kwargs["securities"]

        result = trading_service.get_market_quote(access_token, securities)

        if result.get("success"):
            # Format quotes for output
            quotes = []
            data = result.get("data", {})

            # Handle nested structure
            if isinstance(data, dict):
                # Try to extract quotes from nested structure
                for exchange_seg, sec_dict in securities.items():
                    if exchange_seg in data:
                        segment_data = data[exchange_seg]
                        if isinstance(segment_data, dict):
                            for sec_id in sec_dict:
                                quote_data = segment_data.get(str(sec_id)) or segment_data.get(sec_id)
                                if quote_data:
                                    quotes.append(self._format_quote(sec_id, exchange_seg, quote_data))

            return {
                "success": True,
                "quotes": quotes
            }
        else:
            return {"success": False, "error": result.get("error", "Failed to fetch quotes")}

    def _format_quote(self, security_id: int, exchange_segment: str, quote_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format quote data for output"""
        ohlc = quote_data.get("ohlc") or quote_data.get("OHLC") or {}
        if not isinstance(ohlc, dict):
            ohlc = {}

        return {
            "security_id": security_id,
            "exchange_segment": exchange_segment,
            "ltp": self._extract_price(quote_data, ["LTP", "ltp", "lastPrice", "LAST_PRICE"]),
            "open": self._extract_price(ohlc, ["OPEN", "open", "Open"]),
            "high": self._extract_price(ohlc, ["HIGH", "high", "High"]),
            "low": self._extract_price(ohlc, ["LOW", "low", "Low"]),
            "close": self._extract_price(ohlc, ["CLOSE", "close", "Close"]) or self._extract_price(quote_data, ["CLOSE", "close"]),
            "volume": self._extract_volume(quote_data)
        }

    def _extract_price(self, data: Dict[str, Any], keys: list) -> Optional[float]:
        """Extract price value from data using multiple key variations"""
        for key in keys:
            val = data.get(key)
            if val is not None and val != "":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None

    def _extract_volume(self, data: Dict[str, Any]) -> Optional[float]:
        """Extract volume from data"""
        for key in ["VOLUME", "volume", "totalVolume", "TOTAL_VOLUME", "VOL", "vol"]:
            val = data.get(key)
            if val is not None and val != "":
                try:
                    return float(val)
                except (ValueError, TypeError):
                    continue
        return None

