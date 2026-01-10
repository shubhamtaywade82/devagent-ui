"""
Tool executor for DhanHQ API function calls from Ollama/LLM agents

This module handles execution of tool/function calls made by AI agents,
routing them to the appropriate TradingService methods.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
from trading import trading_service


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
        if function_name == "get_market_quote":
            result = trading_service.get_market_quote(
                access_token,
                function_args["securities"]
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

