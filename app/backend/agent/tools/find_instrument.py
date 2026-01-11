"""
Find Instrument Tool

Resolves symbol names to DhanHQ security IDs and exchange segments.
This is the primary tool for instrument resolution.
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
from tool_executor import search_instruments


class FindInstrumentTool(Tool):
    """Resolve symbol to DhanHQ security_id and exchange_segment"""

    name = "find_instrument"
    description = "Search for instruments/securities by symbol name, trading symbol, or underlying symbol. Returns security ID, exchange segment, and instrument details. ALWAYS use this first when user asks about a stock, index, or instrument by name (e.g., 'NIFTY', 'HDFC Bank', 'RELIANCE'). Then use the returned security_id and exchange_segment for other operations."

    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query - symbol name, trading symbol, or underlying symbol (e.g., 'NIFTY', 'HDFC', 'RELIANCE', 'NIFTY 50')"
            },
            "exchange_segment": {
                "type": "string",
                "description": "Optional: Filter by exchange segment (e.g., 'NSE_EQ', 'NSE_FO', 'BSE_EQ', 'IDX_I' for indices). Leave empty to search all segments.",
                "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "IDX_I", "MCX_COM", "NCDEX_COM"]
            },
            "instrument_type": {
                "type": "string",
                "description": "Optional: Filter by instrument type (e.g., 'EQUITY', 'INDEX', 'FUTURES', 'OPTIONS')",
                "enum": ["EQUITY", "INDEX", "FUTURES", "OPTIONS", "COMMODITY"]
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of results to return (default: 10)",
                "default": 20
            },
            "exact_match": {
                "type": "boolean",
                "description": "Whether to perform exact symbol matching (default: false)",
                "default": False
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search should be case sensitive (default: false)",
                "default": False
            }
        },
        "required": ["query"]
    }

    output_schema = {
        "type": "object",
        "properties": {
            "instruments": {
                "type": "array",
                "description": "List of matching instruments",
                "items": {
                    "type": "object",
                    "properties": {
                        "security_id": {"type": "integer"},
                        "exchange_segment": {"type": "string"},
                        "symbol_name": {"type": "string"},
                        "display_name": {"type": "string"},
                        "instrument_type": {"type": "string"}
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

    async def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Execute instrument search"""
        is_valid, error = self.validate_input(**kwargs)
        if not is_valid:
            return {"success": False, "error": error}

        query = kwargs["query"]
        exchange_segment = kwargs.get("exchange_segment")
        instrument_type = kwargs.get("instrument_type")
        limit = kwargs.get("limit", 10)
        exact_match = kwargs.get("exact_match", False)
        case_sensitive = kwargs.get("case_sensitive", False)

        result = await search_instruments(
            query=query,
            exchange_segment=exchange_segment,
            instrument_type=instrument_type,
            limit=limit,
            exact_match=exact_match,
            case_sensitive=case_sensitive
        )

        if result.get("success"):
            instruments = result.get("data", {}).get("instruments", [])
            # Format instruments for output
            formatted_instruments = []
            for inst in instruments:
                # Handle both raw instrument data and pre-formatted data from find_instrument_by_segment
                # Raw data has: SEM_SECURITY_ID, SECURITY_ID, SM_SECURITY_ID
                # Formatted data has: security_id (already extracted)
                security_id = (
                    inst.get("security_id") or  # Already formatted
                    inst.get("SEM_SECURITY_ID") or
                    inst.get("SECURITY_ID") or
                    inst.get("SM_SECURITY_ID")
                )

                # Convert to int if it's a string
                if security_id and isinstance(security_id, str):
                    try:
                        security_id = int(security_id)
                    except (ValueError, TypeError):
                        security_id = None

                # Exchange segment - check if already formatted first
                exchange_segment = inst.get("exchange_segment")
                if not exchange_segment:
                    exchange_segment = self._get_exchange_segment(inst)

                # Symbol and display names
                symbol_name = (
                    inst.get("symbol_name") or  # Already formatted
                    inst.get("SYMBOL_NAME") or
                    inst.get("symbol_name")
                )
                display_name = (
                    inst.get("display_name") or  # Already formatted
                    inst.get("DISPLAY_NAME") or
                    inst.get("SYMBOL_NAME") or
                    symbol_name
                )
                instrument_type = (
                    inst.get("instrument_type") or  # Already formatted
                    inst.get("INSTRUMENT") or
                    inst.get("INSTRUMENT_TYPE")
                )

                # Only add if we have required fields
                if security_id and exchange_segment:
                    formatted_instruments.append({
                        "security_id": security_id,
                        "exchange_segment": exchange_segment,
                        "symbol_name": symbol_name or "N/A",
                        "display_name": display_name or symbol_name or "N/A",
                        "instrument_type": instrument_type or "UNKNOWN"
                    })
                else:
                    # Log warning for debugging
                    print(f"[FindInstrumentTool] Warning: Skipping instrument due to missing fields. security_id={security_id}, exchange_segment={exchange_segment}")
                    print(f"[FindInstrumentTool] Instrument keys: {list(inst.keys())}")
                    print(f"[FindInstrumentTool] Sample values: SEM_SECURITY_ID={inst.get('SEM_SECURITY_ID')}, SECURITY_ID={inst.get('SECURITY_ID')}, security_id={inst.get('security_id')}")

            if not formatted_instruments:
                return {
                    "success": False,
                    "error": f"Found instruments but none had valid security_id and exchange_segment. Check logs for details."
                }

            return {
                "success": True,
                "instruments": formatted_instruments,
                "count": len(formatted_instruments)
            }
        else:
            return {"success": False, "error": result.get("error", "Search failed")}

    def _get_exchange_segment(self, instrument: Dict[str, Any]) -> str:
        """Extract exchange segment from instrument data"""
        exchange = (instrument.get("SEM_EXM_EXCH_ID") or
                   instrument.get("EXCH_ID") or
                   instrument.get("EXCHANGE_ID") or "NSE").upper()
        segment = (instrument.get("SEM_SEGMENT") or
                  instrument.get("SEGMENT") or "E").upper()
        instrument_type = (instrument.get("INSTRUMENT") or
                          instrument.get("INSTRUMENT_TYPE") or "").upper()

        # Handle indices
        if segment == "I" or segment == "INDEX" or instrument_type == "INDEX":
            return "IDX_I"
        elif exchange == "NSE" and segment == "E":
            return "NSE_EQ"
        elif exchange == "BSE" and segment == "E":
            return "BSE_EQ"
        elif exchange == "NSE" and segment == "D":
            return "NSE_FO"
        elif exchange == "BSE" and segment == "D":
            return "BSE_FO"
        elif exchange == "MCX":
            return "MCX_COM"
        elif exchange == "NCDEX":
            return "NCDEX_COM"

        return f"{exchange}_EQ"  # Default fallback

