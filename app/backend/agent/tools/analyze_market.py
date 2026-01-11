"""
Analyze Market Tool

Composite tool that combines current quotes and historical data for trend analysis.
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
from tool_executor import analyze_market_composite


class AnalyzeMarketTool(Tool):
    """Comprehensive market analysis combining current quotes and historical data"""

    name = "analyze_market"
    description = "Comprehensive market analysis combining current quotes and historical data. Fetches current price, recent trend, and provides analysis summary. USE THIS TOOL when users ask about 'trend', 'analysis', 'performance', 'movement', 'direction', or 'how is X doing'. This tool automatically combines current price with historical data to calculate trend direction (up/down/neutral) and percentage change."

    input_schema = {
        "type": "object",
        "properties": {
            "security_id": {
                "type": "integer",
                "description": "Security ID to analyze"
            },
            "exchange_segment": {
                "type": "string",
                "description": "Exchange segment (use IDX_I for indices like NIFTY, SENSEX)",
                "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "IDX_I"]
            },
            "days": {
                "type": "integer",
                "description": "Number of days of historical data to analyze (default: 30)",
                "default": 30
            }
        },
        "required": ["security_id", "exchange_segment"]
    }

    output_schema = {
        "type": "object",
        "properties": {
            "current_price": {"type": "number"},
            "trend": {
                "type": "object",
                "properties": {
                    "change": {"type": "number"},
                    "change_percent": {"type": "number"},
                    "direction": {"type": "string"},
                    "first_price": {"type": "number"},
                    "last_price": {"type": "number"},
                    "days_analyzed": {"type": "integer"}
                }
            },
            "trend_summary": {"type": "string"}
        }
    }

    safety = {
        "read_only": True,
        "requires_confirmation": False
    }

    async def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute market analysis"""
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}

        if not access_token:
            return {"success": False, "error": "Access token required"}

        security_id = kwargs["security_id"]
        exchange_segment = kwargs["exchange_segment"]
        days = kwargs.get("days", 30)

        result = await analyze_market_composite(
            access_token,
            security_id,
            exchange_segment,
            days
        )

        if result.get("success"):
            metrics = result.get("data", {}).get("metrics", {})
            return {
                "success": True,
                "current_price": metrics.get("current_price"),
                "trend": metrics.get("trend"),
                "trend_summary": metrics.get("trend_summary", "")
            }
        else:
            return {"success": False, "error": result.get("error", "Analysis failed")}

