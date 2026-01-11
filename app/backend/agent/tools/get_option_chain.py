"""
Get Option Chain Tool

Fetch option chain for an underlying with strict contracts.
Note: DhanHQ requires an expiry_date for option_chain.
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
    from agent.validation.schemas import OptionChainWithExpirySchema
except ImportError:
    from app.agent.validation.schemas import OptionChainWithExpirySchema


class GetOptionChainTool(Tool):
    name = "get_option_chain"
    description = (
        "Fetch option chain for an underlying. "
        "Requires underlying_security_id, exchange_segment, and expiry_date (YYYY-MM-DD)."
    )

    input_schema = OptionChainWithExpirySchema

    output_schema = {"type": "object", "properties": {"data": {}, "raw": {}}}

    safety = {"read_only": True, "requires_confirmation": False}

    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}
        if not access_token:
            return {"success": False, "error": "Access token required"}

        # Normalize naming into trading_service signature
        underlying_security_id = kwargs["underlying_security_id"]
        exchange_segment = kwargs["exchange_segment"]
        expiry_date = kwargs["expiry_date"]

        result = trading_service.get_option_chain(
            access_token=access_token,
            under_security_id=int(underlying_security_id),
            under_exchange_segment=exchange_segment,
            expiry=expiry_date,
        )

        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Failed to fetch option chain")}

        return {"success": True, "data": result.get("data")}

