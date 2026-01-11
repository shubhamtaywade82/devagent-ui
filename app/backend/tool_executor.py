"""
Tool executor for DhanHQ API function calls from Ollama/LLM agents

This module handles execution of tool/function calls made by AI agents,
routing them to the appropriate TradingService methods.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os
from trading import trading_service
from database import Database


def get_access_token(access_token: Optional[str] = None) -> Optional[str]:
    """
    Get access token with fallback to environment variable.

    Args:
        access_token: Provided access token (from request/parameter)

    Returns:
        Access token from parameter or environment variable, or None if neither exists
    """
    if access_token:
        return access_token
    return os.getenv("DHAN_ACCESS_TOKEN")


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
    # Use provided token or fallback to environment variable
    access_token = get_access_token(access_token)

    if not access_token:
        return {
            "success": False,
            "error": "Access token required for trading operations. Please provide access_token parameter or set DHAN_ACCESS_TOKEN environment variable."
        }

    try:
        # Route to appropriate TradingService method
        if function_name == "search_instruments":
            # Search instruments (supports exact_match and case_sensitive like Ruby gem)
            return await search_instruments(
                function_args.get("query", ""),
                function_args.get("exchange_segment"),
                function_args.get("instrument_type"),
                function_args.get("limit", 10),
                function_args.get("exact_match", False),
                function_args.get("case_sensitive", False)
            )
        elif function_name == "get_market_quote":
            # Handle IDX_I format for indices - use IDX_I directly (DhanHQ API supports it)
            securities = function_args["securities"]
            # Use securities as-is - DhanHQ API should handle IDX_I correctly
            print(f"[get_market_quote] Calling with securities: {securities}")

            result = trading_service.get_market_quote(
                access_token,
                securities
            )

            # Log the result for debugging
            if result.get("success"):
                print(f"[get_market_quote] Success - data keys: {list(result.get('data', {}).keys()) if isinstance(result.get('data'), dict) else 'not a dict'}")
            else:
                print(f"[get_market_quote] Failed - error: {result.get('error')}")

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


async def find_instrument_by_segment(
    exchange_segment: str,
    symbol: str,
    exact_match: bool = False,
    case_sensitive: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Find a specific instrument by exchange segment and symbol (similar to Ruby gem's Instrument.find)

    Matching priority (for all instrument types):
    1. underlying_symbol (highest priority)
    2. symbol_name
    3. display_name (lowest priority)

    Args:
        exchange_segment: Exchange segment (e.g., "NSE_EQ", "IDX_I")
        symbol: Symbol name to search for
        exact_match: Whether to perform exact matching (default: False)
        case_sensitive: Whether search should be case sensitive (default: False)

    Returns:
        Dict with instrument data or None if not found
    """
    try:
        # Fetch instruments from API for the segment
        segment_result = await trading_service.get_instrument_list_segmentwise(exchange_segment)
        if not segment_result.get("success") or not segment_result.get("data", {}).get("instruments"):
            print(f"Warning: Failed to fetch instruments for segment {exchange_segment}: {segment_result.get('error', 'Unknown error')}")
            return None

        instruments = segment_result["data"]["instruments"]
        search_symbol = symbol if case_sensitive else symbol.upper()
        print(f"Searching for '{search_symbol}' in {len(instruments)} instruments from segment {exchange_segment}")

        # Two-pass approach: First pass for exact matches, second pass for contains matches
        # This ensures exact matches are always prioritized, even if contains matches appear earlier in the list

        def process_instrument(inst, collect_contains=False):
            """Process a single instrument and return match info if found"""
            inst_type = (inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "").upper()

            # Get all fields (normalize case if needed)
            underlying_symbol = inst.get("UNDERLYING_SYMBOL") or ""
            symbol_name = inst.get("SYMBOL_NAME") or ""
            display_name = inst.get("DISPLAY_NAME") or ""
            trading_symbol = inst.get("TRADING_SYMBOL") or inst.get("SEM_TRADING_SYMBOL") or ""

            if not case_sensitive:
                underlying_symbol = underlying_symbol.upper().strip()
                symbol_name = symbol_name.upper().strip()
                display_name = display_name.upper().strip()
                trading_symbol = trading_symbol.upper().strip()

            match_priority = None
            match_field = None

            # Try EXACT matches first
            if underlying_symbol == search_symbol:
                match_priority = 1
                match_field = "underlying_symbol"
                print(f"Found EXACT match by underlying_symbol: {inst.get('UNDERLYING_SYMBOL')}")
            elif symbol_name == search_symbol:
                match_priority = 2
                match_field = "symbol_name"
                print(f"Found EXACT match by symbol_name: {inst.get('SYMBOL_NAME')}")
            elif display_name == search_symbol:
                match_priority = 3
                match_field = "display_name"
                print(f"Found EXACT match by display_name: {inst.get('DISPLAY_NAME')}")
            # Only check contains matches if collect_contains is True
            elif collect_contains and not exact_match:
                if underlying_symbol and search_symbol in underlying_symbol:
                    match_priority = 4
                    match_field = "underlying_symbol"
                    print(f"Found CONTAINS match by underlying_symbol: {inst.get('UNDERLYING_SYMBOL')}")
                elif symbol_name and search_symbol in symbol_name:
                    match_priority = 5
                    match_field = "symbol_name"
                    print(f"Found CONTAINS match by symbol_name: {inst.get('SYMBOL_NAME')}")
                elif display_name and search_symbol in display_name:
                    match_priority = 6
                    match_field = "display_name"
                    print(f"Found CONTAINS match by display_name: {inst.get('DISPLAY_NAME')}")
                elif trading_symbol and search_symbol in trading_symbol:
                    match_priority = 7
                    match_field = "trading_symbol"
                    print(f"Found CONTAINS match by trading_symbol: {trading_symbol}")

            if match_priority is None:
                return None

            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or inst.get("SM_SECURITY_ID")
            exchange = inst.get("EXCH_ID") or inst.get("SEM_EXM_EXCH_ID") or "NSE"
            segment = inst.get("SEGMENT") or inst.get("SEM_SEGMENT") or ""

            # Map exchange segment correctly - ensure indices use IDX_I
            final_exchange_segment = exchange_segment
            segment_upper = segment.upper()
            if segment_upper == "I" or segment_upper == "INDEX" or inst_type == "INDEX":
                final_exchange_segment = "IDX_I"
            elif exchange_segment == "IDX_I" and segment_upper != "I":
                return None  # Skip if we requested IDX_I but this isn't an index

            return {
                "priority": match_priority,
                "field": match_field,
                "instrument": {
                    "security_id": int(security_id) if security_id else None,
                    "exchange_segment": final_exchange_segment,
                    "symbol_name": inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME", ""),
                    "trading_symbol": inst.get("TRADING_SYMBOL", ""),
                    "display_name": inst.get("DISPLAY_NAME") or inst.get("SYMBOL_NAME", ""),
                    "underlying_symbol": inst.get("UNDERLYING_SYMBOL", ""),
                    "instrument_type": inst_type,
                    "exchange": exchange,
                    "segment": segment
                }
            }

        # PASS 1: Search for EXACT matches only (priority 1-3)
        exact_matches = []
        for inst in instruments:
            match_info = process_instrument(inst, collect_contains=False)
            if match_info and match_info["priority"] <= 3:  # Only exact matches
                exact_matches.append(match_info)

        # If we found exact matches, return the best one immediately
        if exact_matches:
            exact_matches.sort(key=lambda x: x["priority"])
            best_match = exact_matches[0]["instrument"]
            print(f"Selected best EXACT match: {best_match.get('symbol_name')} / {best_match.get('display_name')} / {best_match.get('underlying_symbol')} (Priority: {exact_matches[0]['priority']}, Security ID: {best_match.get('security_id')}, Exchange Segment: {best_match.get('exchange_segment')})")
            return best_match

        # PASS 2: Only if no exact matches, search for CONTAINS matches (priority 4-7)
        if not exact_match:
            contains_matches = []
            for inst in instruments:
                match_info = process_instrument(inst, collect_contains=True)
                if match_info and match_info["priority"] >= 4:  # Only contains matches
                    contains_matches.append(match_info)

            if contains_matches:
                contains_matches.sort(key=lambda x: x["priority"])
                best_match = contains_matches[0]["instrument"]
                print(f"Selected best CONTAINS match: {best_match.get('symbol_name')} / {best_match.get('display_name')} / {best_match.get('underlying_symbol')} (Priority: {contains_matches[0]['priority']}, Security ID: {best_match.get('security_id')}, Exchange Segment: {best_match.get('exchange_segment')})")
                return best_match

        print(f"No match found for '{search_symbol}' in segment {exchange_segment}")
        return None
    except Exception as e:
        print(f"Error in find_instrument_by_segment: {str(e)}")
        return None


async def search_instruments(
    query: str,
    exchange_segment: Optional[str] = None,
    instrument_type: Optional[str] = None,
    limit: int = 10,
    exact_match: bool = False,
    case_sensitive: bool = False
) -> Dict[str, Any]:
    """
    Search for instruments/securities (similar to Ruby gem's Instrument.find and find_anywhere)

    Matching priority (for all instrument types):
    1. underlying_symbol (highest priority)
    2. symbol_name
    3. display_name (lowest priority)

    Args:
        query: Search query (symbol name, trading symbol, etc.)
        exchange_segment: Optional exchange segment filter (if None, searches common segments)
        instrument_type: Optional instrument type filter
        limit: Maximum number of results
        exact_match: Whether to perform exact matching (default: False)
        case_sensitive: Whether search should be case sensitive (default: False)

    Returns:
        Dict with search results including security_id, exchange_segment, etc.
    """
    try:
        # If exchange_segment is provided, use find_instrument_by_segment (like Ruby gem's find)
        if exchange_segment:
            result = await find_instrument_by_segment(exchange_segment, query, exact_match, case_sensitive)
            if result:
                return {
                    "success": True,
                    "data": {
                        "instruments": [result],
                        "count": 1,
                        "query": query
                    }
                }
            else:
                return {
                    "success": False,
                    "error": f"No instrument found matching '{query}' in segment '{exchange_segment}'"
                }

        # If no exchange_segment, search across common segments (like Ruby gem's find_anywhere)
        common_segments = ["NSE_EQ", "BSE_EQ", "IDX_I", "NSE_FO", "BSE_FO"]
        if instrument_type:
            # Filter segments based on instrument type
            if instrument_type.upper() == "INDEX":
                common_segments = ["IDX_I"]
            elif instrument_type.upper() == "EQUITY":
                common_segments = ["NSE_EQ", "BSE_EQ"]
            elif instrument_type.upper() in ["FUTURES", "OPTIONS"]:
                common_segments = ["NSE_FO", "BSE_FO"]

        # Try each segment until we find a match
        for segment in common_segments:
            result = await find_instrument_by_segment(segment, query, exact_match, case_sensitive)
            if result:
                return {
                    "success": True,
                    "data": {
                        "instruments": [result],
                        "count": 1,
                        "query": query
                    }
                }

        # If no match found, try to fetch and show sample instruments for debugging
        # Start with IDX_I for index queries, or NSE_EQ for others
        sample_segment = "IDX_I" if (instrument_type and instrument_type.upper() == "INDEX") or "NIFTY" in query.upper() or "SENSEX" in query.upper() else "NSE_EQ"
        segment_result = await trading_service.get_instrument_list_segmentwise(sample_segment)

        sample_instruments = []
        if segment_result.get("success") and segment_result.get("data", {}).get("instruments"):
            idx_instruments = segment_result["data"]["instruments"]
            # Show first 30 instruments and also search for any that might match
            query_upper = query.upper()
            for inst in idx_instruments[:30]:
                underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or "").upper().strip()
                symbol_name = (inst.get("SYMBOL_NAME") or "").upper().strip()
                display_name = (inst.get("DISPLAY_NAME") or "").upper().strip()
                trading_symbol = (inst.get("TRADING_SYMBOL") or "").upper().strip()
                security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or ""
                inst_type = (inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "").upper()

                # Check if this might be a match (for debugging)
                might_match = False
                if query_upper in symbol_name or query_upper in display_name or query_upper in underlying_symbol or query_upper in trading_symbol:
                    might_match = True

                sample_instruments.append({
                    "underlying_symbol": underlying_symbol,
                    "symbol_name": symbol_name,
                    "display_name": display_name,
                    "trading_symbol": trading_symbol,
                    "security_id": security_id,
                    "instrument_type": inst_type,
                    "might_match": might_match  # Flag potential matches
                })

        # Find potential matches in sample instruments for better error message
        potential_matches = [inst for inst in sample_instruments if inst.get("might_match", False)]

        error_msg = f"No instruments found matching '{query}' across segments {common_segments}."
        if potential_matches:
            error_msg += f"\n\nFound {len(potential_matches)} potential matches in sample instruments:"
            for match in potential_matches[:5]:
                error_msg += f"\n  - {match.get('symbol_name')} (symbol_name) / {match.get('display_name')} (display_name) / {match.get('underlying_symbol')} (underlying_symbol) / {match.get('trading_symbol')} (trading_symbol) - Security ID: {match.get('security_id')}"

        return {
            "success": False,
            "error": error_msg,
            "data": {
                "query": query,
                "searched_segments": common_segments,
                "sample_instruments": sample_instruments[:20] if sample_instruments else None,
                "potential_matches": potential_matches[:5] if potential_matches else [],
                "hint": "For EQUITY instruments, search uses underlying_symbol. For INDEX instruments, search checks symbol_name, display_name, underlying_symbol, and trading_symbol. Check sample_instruments to see available fields."
            }
        }

    except Exception as e:
        error_detail = str(e) if str(e) else repr(e)
        import traceback
        print(f"Error in search_instruments: {error_detail}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": f"Error searching instruments: {error_detail}"
        }

        # Normalize query and detect if it's an index query
        query_upper = query.upper().strip() if not case_sensitive else query.strip()
        is_index_query = (
            (instrument_type and instrument_type.upper() == "INDEX") or
            "NIFTY" in query_upper or
            "SENSEX" in query_upper
        )

        # Get all instruments from database
        try:
            instruments = await db.get_instruments("detailed", limit=50000)
            if not instruments:
                # If database is empty, try to fetch from CSV as fallback
                print("Database is empty, trying to fetch from CSV...")
                csv_result = trading_service.get_instrument_list_csv("detailed")
                if csv_result.get("success") and csv_result.get("data", {}).get("instruments"):
                    instruments = csv_result["data"]["instruments"]
                    # Optionally save to DB for future use
                    try:
                        await db.save_instruments(instruments, "detailed")
                    except Exception as e:
                        print(f"Warning: Could not save instruments to database: {e}")
                else:
                    instruments = []
        except Exception as e:
            print(f"Error fetching instruments from database: {str(e)}")
            # Try CSV as fallback
            try:
                csv_result = trading_service.get_instrument_list_csv("detailed")
                if csv_result.get("success") and csv_result.get("data", {}).get("instruments"):
                    instruments = csv_result["data"]["instruments"]
                else:
                    instruments = []
            except Exception as csv_error:
                print(f"Error fetching instruments from CSV: {str(csv_error)}")
                instruments = []

        # Two-pass approach: First pass for exact matches, second pass for contains matches
        def process_db_instrument(inst, collect_contains=False):
            """Process a single database instrument and return match info if found"""
            # Check various fields
            symbol_name = (inst.get("SYMBOL_NAME") or inst.get("SEM_SYMBOL_NAME") or inst.get("SM_SYMBOL_NAME") or "").upper()
            trading_symbol = (inst.get("SEM_TRADING_SYMBOL") or inst.get("TRADING_SYMBOL") or "").upper()
            display_name = (inst.get("DISPLAY_NAME") or inst.get("SEM_CUSTOM_SYMBOL") or "").upper()
            underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or inst.get("SEM_UNDERLYING_SYMBOL") or "").upper()
            security_id = str(inst.get("SEM_SECURITY_ID") or inst.get("SECURITY_ID") or inst.get("SM_SECURITY_ID") or "")

            # Get segment and exchange for filtering
            segment = (inst.get("SEM_SEGMENT") or inst.get("SEGMENT") or "").upper()
            exchange = (inst.get("SEM_EXM_EXCH_ID") or inst.get("EXCH_ID") or inst.get("EXCHANGE_ID") or "").upper()

            # For index queries, must have segment "I"
            if is_index_query:
                if segment != "I":
                    return None

            match_priority = None

            # Try EXACT matches first
            if underlying_symbol:
                underlying_symbol_clean = underlying_symbol.strip()
                if underlying_symbol_clean == query_upper:
                    match_priority = 1
            elif symbol_name:
                symbol_name_clean = symbol_name.strip()
                if symbol_name_clean == query_upper:
                    match_priority = 2
            elif display_name:
                display_name_clean = display_name.strip()
                if display_name_clean == query_upper:
                    match_priority = 3
            # Only check contains matches if collect_contains is True
            elif collect_contains and not exact_match:
                if underlying_symbol and query_upper in underlying_symbol:
                    match_priority = 4
                elif symbol_name and query_upper in symbol_name:
                    match_priority = 5
                elif display_name and query_upper in display_name:
                    match_priority = 6
                elif trading_symbol and query_upper in trading_symbol:
                    match_priority = 7
                elif query_upper == security_id:
                    match_priority = 8

            if match_priority is None:
                return None

            # Apply filters if provided
            if exchange_segment:
                # Handle IDX_I specially
                if exchange_segment == "IDX_I":
                    if segment != "I":
                        return None
                else:
                    expected_exchange = exchange_segment.split("_")[0]
                    expected_segment = exchange_segment.split("_")[1] if "_" in exchange_segment else ""
                    segment_map = {"EQ": "E", "FNO": "D", "FO": "D", "IDX": "I", "COM": "M"}
                    expected_segment_code = segment_map.get(expected_segment, expected_segment)
                    if exchange.upper() != expected_exchange.upper() or (expected_segment_code and segment != expected_segment_code):
                        return None

            if instrument_type:
                inst_type = (inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "").upper()
                if inst_type != instrument_type.upper():
                    return None

            # Extract relevant information
            security_id_val = inst.get("SEM_SECURITY_ID") or inst.get("SECURITY_ID") or inst.get("SM_SECURITY_ID")
            exchange_val = inst.get("SEM_EXM_EXCH_ID") or inst.get("EXCH_ID") or inst.get("EXCHANGE_ID") or "NSE"
            segment_val = inst.get("SEM_SEGMENT") or inst.get("SEGMENT") or "E"

            # Map to DhanHQ exchange segment format
            exchange_segment_formatted = "NSE_EQ"
            segment_upper = segment_val.upper()
            exchange_upper = exchange_val.upper()

            if segment_upper == "I" or segment_upper == "INDEX":
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

            return {
                "priority": match_priority,
                "result": {
                    "security_id": int(security_id_val) if security_id_val else None,
                    "exchange_segment": exchange_segment_formatted,
                    "symbol_name": inst.get("SYMBOL_NAME") or inst.get("SEM_SYMBOL_NAME") or "",
                    "trading_symbol": inst.get("SEM_TRADING_SYMBOL") or inst.get("TRADING_SYMBOL") or "",
                    "display_name": inst.get("DISPLAY_NAME") or inst.get("SEM_CUSTOM_SYMBOL") or "",
                    "instrument_type": inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "",
                    "exchange": exchange_val,
                    "segment": segment_val
                }
            }

        # PASS 1: Search for EXACT matches only (priority 1-3)
        exact_results = []
        for inst in instruments:
            match_info = process_db_instrument(inst, collect_contains=False)
            if match_info and match_info["priority"] <= 3:
                exact_results.append(match_info)

        # If we found exact matches, use them (sorted and limited)
        if exact_results:
            exact_results.sort(key=lambda x: x["priority"])
            results = [item["result"] for item in exact_results[:limit]]
        else:
            # PASS 2: Only if no exact matches, search for CONTAINS matches (priority 4-8)
            if not exact_match:
                contains_results = []
                for inst in instruments:
                    match_info = process_db_instrument(inst, collect_contains=True)
                    if match_info and match_info["priority"] >= 4:
                        contains_results.append(match_info)

                if contains_results:
                    contains_results.sort(key=lambda x: x["priority"])
                    results = [item["result"] for item in contains_results[:limit]]
                else:
                    results = []
            else:
                results = []

        if not results:
            # If no results found, try to fetch and show sample instruments from API
            sample_instruments = []
            sample_info = ""

            # For index queries, fetch IDX_I instruments to show samples
            if is_index_query:
                try:
                    segment_result = await trading_service.get_instrument_list_segmentwise("IDX_I")
                    if segment_result.get("success") and segment_result.get("data", {}).get("instruments"):
                        idx_instruments = segment_result["data"]["instruments"]
                        # Show first 20 instruments as samples
                        for inst in idx_instruments[:20]:
                            underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or inst.get("UNDERLYING") or "").upper().strip()
                            symbol_name = inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME") or ""
                            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or ""
                            sample_instruments.append({
                                "underlying_symbol": underlying_symbol,
                                "symbol_name": symbol_name,
                                "security_id": security_id,
                                "display_name": inst.get("DISPLAY_NAME", ""),
                                "trading_symbol": inst.get("TRADING_SYMBOL", "")
                            })
                        sample_info = f"\n\nFound {len(idx_instruments)} total instruments in IDX_I segment. Sample instruments:\n" + "\n".join([
                            f"  - {inst['symbol_name']} (underlying_symbol: {inst['underlying_symbol']}, security_id: {inst['security_id']})"
                            for inst in sample_instruments[:10]
                        ])
                except Exception as e:
                    print(f"Error fetching sample instruments: {str(e)}")

            # If no results found, provide helpful error message with samples
            error_msg = f"No instruments found matching '{query}'. Please check the spelling or try a different search term. For indices like NIFTY, ensure you're searching with the correct name.{sample_info}"

            return {
                "success": False,
                "error": error_msg,
                "data": {
                    "query": query,
                    "sample_instruments": sample_instruments[:10] if sample_instruments else None,
                    "hint": "Check the sample_instruments above to see available instruments. Look for matching underlying_symbol or symbol_name."
                } if sample_instruments else None
            }

        return {
            "success": True,
            "data": {
                "instruments": results,
                "count": len(results),
                "query": query
            }
        }

    except Exception as e:
        error_detail = str(e) if str(e) else repr(e)
        import traceback
        print(f"Error in search_instruments: {error_detail}")
        print(traceback.format_exc())
        return {
            "success": False,
            "error": f"Error searching instruments: {error_detail}"
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

