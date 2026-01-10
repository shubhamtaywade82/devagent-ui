"""
Tool executor for DhanHQ API function calls from Ollama/LLM agents

This module handles execution of tool/function calls made by AI agents,
routing them to the appropriate TradingService methods.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from trading import trading_service
from database import Database


async def execute_tool(
    function_name: str,
    function_args: Dict[str, Any],
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a tool/function call from Ollama/LLM agent

    Args:
        function_name: Name of the function to execute
        function_args: Arguments for the function (from LLM)
        access_token: DhanHQ access token (required for most operations)

    Returns:
        Dict with function execution results
    """
    if not access_token:
        return {
            "success": False,
            "error": "Access token required for trading operations. Please authenticate first."
        }

    try:
        # Route to appropriate TradingService method
        if function_name == "search_instruments":
            # Search instruments in database
            return await search_instruments(
                function_args.get("query", ""),
                function_args.get("exchange_segment"),
                function_args.get("instrument_type"),
                function_args.get("limit", 10)
            )
        elif function_name == "get_market_quote":
            # Handle IDX_I format for indices - convert to proper format for DhanHQ API
            securities = function_args["securities"]
            # If IDX_I is used, we need to handle it specially
            # DhanHQ API might need it in a different format
            processed_securities = {}
            for exchange_seg, security_ids in securities.items():
                if exchange_seg == "IDX_I":
                    # For indices, try both IDX_I and NSE_IDX formats
                    # Some APIs might accept IDX_I directly, others might need NSE_IDX
                    processed_securities["IDX_I"] = security_ids
                    # Also try NSE_IDX as fallback
                    processed_securities["NSE_IDX"] = security_ids
                else:
                    processed_securities[exchange_seg] = security_ids

            result = trading_service.get_market_quote(
                access_token,
                processed_securities
            )
            return result

        elif function_name == "get_historical_data":
            result = trading_service.get_historical_data(
                access_token,
                function_args["security_id"],
                function_args["exchange_segment"],
                function_args["instrument_type"],
                function_args["from_date"],
                function_args["to_date"],
                function_args.get("interval", "daily")
            )
            return result

        elif function_name == "get_positions":
            result = trading_service.get_positions(access_token)
            return result

        elif function_name == "get_holdings":
            result = trading_service.get_holdings(access_token)
            return result

        elif function_name == "get_fund_limits":
            result = trading_service.get_fund_limits(access_token)
            return result

        elif function_name == "get_option_chain":
            result = trading_service.get_option_chain(
                access_token,
                function_args["under_security_id"],
                function_args["under_exchange_segment"],
                function_args["expiry"]
            )
            return result

        elif function_name == "get_orders":
            result = trading_service.get_orders(access_token)
            return result

        elif function_name == "get_trades":
            result = trading_service.get_trades(access_token)
            return result

        elif function_name == "analyze_market":
            # Composite function that combines multiple API calls
            return await analyze_market_composite(
                access_token,
                function_args["security_id"],
                function_args["exchange_segment"],
                function_args.get("days", 30)
            )

        else:
            return {
                "success": False,
                "error": f"Unknown function: {function_name}. Available functions: {', '.join(TOOL_EXECUTORS.keys())}"
            }

    except KeyError as e:
        return {
            "success": False,
            "error": f"Missing required parameter: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Error executing {function_name}: {str(e)}"
        }


async def search_instruments(
    query: str,
    exchange_segment: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for instruments/securities in the database

    Args:
        query: Search query (symbol name, trading symbol, etc.)
        exchange_segment: Optional exchange segment filter
        instrument_type: Optional instrument type filter
        limit: Maximum number of results

    Returns:
        Dict with search results including security_id, exchange_segment, etc.
    """
    try:
        db = Database()

        # For indices like NIFTY, SENSEX, try to get from IDX_I segment directly first
        query_upper = query.upper().strip()
        if instrument_type and instrument_type.upper() == "INDEX":
            try:
                # Try to get instruments from IDX_I segment using API
                segment_result = await trading_service.get_instrument_list_segmentwise("IDX_I")
                if segment_result.get("success") and segment_result.get("data", {}).get("instruments"):
                    idx_instruments = segment_result["data"]["instruments"]
                    # Search in IDX_I instruments
                    for inst in idx_instruments:
                        symbol_name = (inst.get("SYMBOL_NAME") or "").upper()
                        if query_upper in symbol_name or symbol_name == query_upper:
                            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or inst.get("SM_SECURITY_ID")
                            exchange = inst.get("EXCH_ID") or inst.get("SEM_EXM_EXCH_ID") or "NSE"
                            if security_id:
                                return {
                                    "success": True,
                                    "data": {
                                        "instruments": [{
                                            "security_id": int(security_id),
                                            "exchange_segment": "IDX_I",
                                            "symbol_name": inst.get("SYMBOL_NAME", ""),
                                            "trading_symbol": inst.get("TRADING_SYMBOL", ""),
                                            "display_name": inst.get("DISPLAY_NAME", ""),
                                            "instrument_type": "INDEX",
                                            "exchange": exchange,
                                            "segment": "I"
                                        }],
                                        "count": 1,
                                        "query": query
                                    }
                                }
            except Exception as e:
                pass

        # Get all instruments from database
        instruments = await db.get_instruments("detailed", limit=50000)

        # Filter instruments
        results = []
        for inst in instruments:
            # Check various fields
            symbol_name = (inst.get("SYMBOL_NAME") or inst.get("SEM_SYMBOL_NAME") or inst.get("SM_SYMBOL_NAME") or "").upper()
            trading_symbol = (inst.get("SEM_TRADING_SYMBOL") or inst.get("TRADING_SYMBOL") or "").upper()
            display_name = (inst.get("DISPLAY_NAME") or inst.get("SEM_CUSTOM_SYMBOL") or "").upper()
            underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or inst.get("SEM_UNDERLYING_SYMBOL") or "").upper()
            security_id = str(inst.get("SEM_SECURITY_ID") or inst.get("SECURITY_ID") or inst.get("SM_SECURITY_ID") or "")

            # Check if query matches
            matches = (
                query_upper in symbol_name or
                query_upper in trading_symbol or
                query_upper in display_name or
                query_upper in underlying_symbol or
                query_upper == security_id
            )

            if not matches:
                continue

            # Apply filters if provided
            if exchange_segment:
                exchange = inst.get("SEM_EXM_EXCH_ID") or inst.get("EXCH_ID") or inst.get("EXCHANGE_ID") or ""
                segment = inst.get("SEM_SEGMENT") or inst.get("SEGMENT") or ""

                exchange_upper = exchange.upper()
                segment_upper = segment.upper()

                # Handle IDX_I specially
                if exchange_segment == "IDX_I":
                    if segment_upper != "I":
                        continue
                else:
                    expected_exchange = exchange_segment.split("_")[0]
                    expected_segment = exchange_segment.split("_")[1] if "_" in exchange_segment else ""
                    segment_map = {"EQ": "E", "FNO": "D", "FO": "D", "IDX": "I", "COM": "M"}
                    expected_segment_code = segment_map.get(expected_segment, expected_segment)
                    if exchange_upper != expected_exchange or (expected_segment_code and segment_upper != expected_segment_code):
                        continue

            if instrument_type:
                inst_type = (inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "").upper()
                if inst_type != instrument_type.upper():
                    continue

            # Extract relevant information
            security_id_val = inst.get("SEM_SECURITY_ID") or inst.get("SECURITY_ID") or inst.get("SM_SECURITY_ID")
            exchange_val = inst.get("SEM_EXM_EXCH_ID") or inst.get("EXCH_ID") or inst.get("EXCHANGE_ID") or "NSE"
            segment_val = inst.get("SEM_SEGMENT") or inst.get("SEGMENT") or "E"

            # Map to DhanHQ exchange segment format
            exchange_segment_formatted = "NSE_EQ"
            segment_upper = segment_val.upper()
            exchange_upper = exchange_val.upper()

            if segment_upper == "I" or segment_upper == "INDEX":
                # Indices use IDX_I format regardless of exchange
                exchange_segment_formatted = "IDX_I"
            elif exchange_upper == "NSE" and segment_upper == "E":
                exchange_segment_formatted = "NSE_EQ"
            elif exchange_upper == "BSE" and segment_upper == "E":
                exchange_segment_formatted = "BSE_EQ"
            elif exchange_upper == "NSE" and segment_upper == "D":
                exchange_segment_formatted = "NSE_FO"
            elif exchange_upper == "BSE" and segment_upper == "D":
                exchange_segment_formatted = "BSE_FO"
            elif exchange_upper == "MCX":
                exchange_segment_formatted = "MCX_COM"
            elif exchange_upper == "NCDEX":
                exchange_segment_formatted = "NCDEX_COM"

            results.append({
                "security_id": int(security_id_val) if security_id_val else None,
                "exchange_segment": exchange_segment_formatted,
                "symbol_name": inst.get("SYMBOL_NAME") or inst.get("SEM_SYMBOL_NAME") or "",
                "trading_symbol": inst.get("SEM_TRADING_SYMBOL") or inst.get("TRADING_SYMBOL") or "",
                "display_name": inst.get("DISPLAY_NAME") or inst.get("SEM_CUSTOM_SYMBOL") or "",
                "instrument_type": inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "",
                "exchange": exchange_val,
                "segment": segment_val
            })

            if len(results) >= limit:
                break

        return {
            "success": True,
            "data": {
                "instruments": results,
                "count": len(results),
                "query": query
            }
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Error searching instruments: {str(e)}"
        }


async def analyze_market_composite(
    access_token: str,
    security_id: int,
    exchange_segment: str,
    days: int = 30
) -> Dict[str, Any]:
    """
    Composite function that combines multiple API calls for comprehensive market analysis

    This is an example of how to create higher-level analysis functions
    that combine multiple DhanHQ API calls.
    """
    try:
        # Calculate date range
        to_date = datetime.now().strftime("%Y-%m-%d")
        from_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        # Get current quote
        quote_result = trading_service.get_market_quote(
            access_token,
            {exchange_segment: [security_id]}
        )

        # Get historical data
        historical_result = trading_service.get_historical_data(
            access_token,
            security_id,
            exchange_segment,
            "EQUITY",  # Default to EQUITY, could be made configurable
            from_date,
            to_date,
            "daily"
        )

        # Combine results
        analysis = {
            "success": True,
            "data": {
                "current_quote": quote_result.get("data") if quote_result.get("success") else None,
                "historical_data": historical_result.get("data") if historical_result.get("success") else None,
                "analysis_period": {
                    "from_date": from_date,
                    "to_date": to_date,
                    "days": days
                },
                "security_id": security_id,
                "exchange_segment": exchange_segment
            }
        }

        # Add basic analysis if data is available
        if quote_result.get("success") and historical_result.get("success"):
            quote_data = quote_result.get("data", {})
            historical_data = historical_result.get("data", {})

            # Extract key metrics
            current_price = None
            if quote_data and isinstance(quote_data, dict):
                # Extract LTP or close price from quote
                current_price = quote_data.get("LTP") or quote_data.get("close") or quote_data.get("lastPrice")

            # Calculate trend if historical data available
            trend = None
            if historical_data and isinstance(historical_data, list) and len(historical_data) > 0:
                # Get first and last close prices
                first_close = historical_data[0].get("close") if isinstance(historical_data[0], dict) else None
                last_close = historical_data[-1].get("close") if isinstance(historical_data[-1], dict) else None

                if first_close and last_close:
                    change = last_close - first_close
                    change_pct = (change / first_close) * 100 if first_close > 0 else 0
                    trend = {
                        "change": change,
                        "change_percent": round(change_pct, 2),
                        "direction": "up" if change > 0 else "down" if change < 0 else "neutral"
                    }

            analysis["data"]["metrics"] = {
                "current_price": current_price,
                "trend": trend
            }

        return analysis

    except Exception as e:
        return {
            "success": False,
            "error": f"Error in market analysis: {str(e)}"
        }


# Export available tool names
TOOL_EXECUTORS = {
    "get_market_quote",
    "get_historical_data",
    "get_positions",
    "get_holdings",
    "get_fund_limits",
    "get_option_chain",
    "get_orders",
    "get_trades",
    "analyze_market"
}

