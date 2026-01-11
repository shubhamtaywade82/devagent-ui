"""
Get Intraday OHLCV Tool

Explicit intraday OHLCV fetch with strict contracts (no silent defaults).
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

try:
    from agent.validation.schemas import IntradayOHLCVSchema
except ImportError:
    from app.agent.validation.schemas import IntradayOHLCVSchema


class GetIntradayOHLCVTool(Tool):
    name = "get_intraday_ohlcv"
    description = (
        "Fetch intraday OHLCV candles for analysis. "
        "Requires explicit interval and date range (YYYY-MM-DD)."
    )

    input_schema = IntradayOHLCVSchema

    output_schema = {
        "type": "object",
        "properties": {
            "data": {"type": "array"},
            "count": {"type": "integer"},
        },
    }

    safety = {"read_only": True, "requires_confirmation": False}

    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}
        if not access_token:
            return {"success": False, "error": "Access token required"}

        result = trading_service.get_historical_data(
            access_token=access_token,
            security_id=kwargs["security_id"],
            exchange_segment=kwargs["exchange_segment"],
            instrument_type=kwargs["instrument_type"],
            from_date=kwargs["from_date"],
            to_date=kwargs["to_date"],
            interval=str(kwargs["interval"]),
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Failed to fetch intraday OHLCV")}

        data = result.get("data", [])
        if not isinstance(data, list):
            data = []
        return {"success": True, "data": data, "count": len(data)}

