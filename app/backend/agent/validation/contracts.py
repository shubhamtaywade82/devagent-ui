"""
Tool contracts: map each tool intent to the canonical schema it must satisfy.

This is the single place that decides which schema guards which tool.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from .schemas import (
    DailyOHLCVSchema,
    IntradayOHLCVSchema,
    MarketQuoteSchema,
    ExpiryListSchema,
    OptionChainWithExpirySchema,
)


SchemaResolver = Callable[[dict], dict]


def resolve_historical_schema(payload: dict) -> dict:
    """
    Legacy compatibility: `get_historical_data` can represent both daily and intraday.
    We choose a schema based on `interval`.
    """
    interval = payload.get("interval")
    if interval is None:
        # Force the guard to ask for interval instead of defaulting.
        # Use the intraday schema so `interval` is required.
        return IntradayOHLCVSchema
    if str(interval).lower() == "daily":
        # Legacy `get_historical_data` MUST still require interval (no silent default).
        return {
            "allOf": [
                DailyOHLCVSchema,
                {
                    "type": "object",
                    "properties": {"interval": {"type": "string", "enum": ["daily"]}},
                    "required": ["interval"],
                },
            ]
        }
    return IntradayOHLCVSchema


TOOL_INPUT_CONTRACTS: Dict[str, dict | SchemaResolver] = {
    # Live market data
    "get_quote": MarketQuoteSchema,
    "get_market_quote": MarketQuoteSchema,  # legacy name

    # New, explicit tools
    "get_intraday_ohlcv": IntradayOHLCVSchema,
    "get_daily_ohlcv": DailyOHLCVSchema,
    "get_expiry_list": ExpiryListSchema,

    # Option chain (concrete fetch requires expiry_date)
    "get_option_chain": OptionChainWithExpirySchema,

    # Legacy / compatibility tools
    "get_historical_data": resolve_historical_schema,
}


def get_schema_for_tool(tool_name: str, payload: dict) -> Optional[dict]:
    resolver = TOOL_INPUT_CONTRACTS.get(tool_name)
    if resolver is None:
        return None
    if callable(resolver):
        return resolver(payload)
    return resolver

