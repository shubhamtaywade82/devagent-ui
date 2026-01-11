"""
Get Expiry List Tool

Fetch available expiry dates for an underlying (F&O).
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


class GetExpiryListTool(Tool):
    name = "get_expiry_list"
    description = "Fetch available expiry dates for an underlying security (F&O)."

    input_schema = {
        "type": "object",
        "properties": {
            "underlying_security_id": {"type": ["string", "integer"]},
            "exchange_segment": {"type": "string"},
        },
        "required": ["underlying_security_id", "exchange_segment"],
    }

    output_schema = {"type": "object", "properties": {"data": {}}}

    safety = {"read_only": True, "requires_confirmation": False}

    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}
        if not access_token:
            return {"success": False, "error": "Access token required"}

        under_security_id = kwargs["underlying_security_id"]
        under_exchange_segment = kwargs["exchange_segment"]

        result = trading_service.get_expiry_list(
            access_token=access_token,
            under_security_id=int(under_security_id),
            under_exchange_segment=str(under_exchange_segment),
        )
        if not result.get("success"):
            return {"success": False, "error": result.get("error", "Failed to fetch expiry list")}
        return {"success": True, "data": result.get("data")}

