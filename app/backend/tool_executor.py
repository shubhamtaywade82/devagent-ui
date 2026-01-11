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


async def find_instrument_by_segment(
    exchange_segment: str,
    symbol: str,
    exact_match: bool = False,
    case_sensitive: bool = False
) -> Optional[Dict[str, Any]]:
    """
    Find a specific instrument by exchange segment and symbol (similar to Ruby gem's Instrument.find)

    For EQUITY instruments: prefers underlying_symbol over symbol_name
    For INDEX/other instruments: uses symbol_name

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

        for inst in instruments:
            # Get instrument type
            inst_type = (inst.get("INSTRUMENT") or inst.get("INSTRUMENT_TYPE") or "").upper()

            matches = False

            # For EQUITY instruments, prefer underlying_symbol over symbol_name (like Ruby gem)
            if inst_type == "EQUITY" and inst.get("UNDERLYING_SYMBOL"):
                instrument_symbol = inst.get("UNDERLYING_SYMBOL")
                if not case_sensitive:
                    instrument_symbol = instrument_symbol.upper()

                # Perform matching
                if exact_match:
                    matches = instrument_symbol == search_symbol
                else:
                    matches = search_symbol in instrument_symbol
            else:
                # For INDEX and other instruments, MUST check both symbol_name AND underlying_symbol
                symbol_name = inst.get("SYMBOL_NAME") or ""
                underlying_symbol = inst.get("UNDERLYING_SYMBOL") or ""

                if not case_sensitive:
                    symbol_name = symbol_name.upper()
                    underlying_symbol = underlying_symbol.upper()

                # Check symbol_name
                symbol_name_matches = False
                if symbol_name:
                    if exact_match:
                        symbol_name_matches = symbol_name == search_symbol
                    else:
                        symbol_name_matches = search_symbol in symbol_name

                # Check underlying_symbol
                underlying_symbol_matches = False
                if underlying_symbol:
                    if exact_match:
                        underlying_symbol_matches = underlying_symbol == search_symbol
                    else:
                        underlying_symbol_matches = search_symbol in underlying_symbol

                # Match if either symbol_name OR underlying_symbol matches
                matches = symbol_name_matches or underlying_symbol_matches

                # Also check display_name and trading_symbol as fallback
                if not matches:
                    display_name = (inst.get("DISPLAY_NAME") or "").upper() if not case_sensitive else (inst.get("DISPLAY_NAME") or "")
                    trading_symbol = (inst.get("TRADING_SYMBOL") or "").upper() if not case_sensitive else (inst.get("TRADING_SYMBOL") or "")

                    if display_name:
                        if exact_match:
                            matches = display_name == search_symbol
                        else:
                            matches = search_symbol in display_name

                    if not matches and trading_symbol:
                        if exact_match:
                            matches = trading_symbol == search_symbol
                        else:
                            matches = search_symbol in trading_symbol

            if matches:
                security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or inst.get("SM_SECURITY_ID")
                exchange = inst.get("EXCH_ID") or inst.get("SEM_EXM_EXCH_ID") or "NSE"
                segment = inst.get("SEGMENT") or inst.get("SEM_SEGMENT") or ""

                print(f"Found match: {inst.get('SYMBOL_NAME')} / {inst.get('DISPLAY_NAME')} / {inst.get('UNDERLYING_SYMBOL')} (Security ID: {security_id})")

                return {
                    "security_id": int(security_id) if security_id else None,
                    "exchange_segment": exchange_segment,
                    "symbol_name": inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME", ""),
                    "trading_symbol": inst.get("TRADING_SYMBOL", ""),
                    "display_name": inst.get("DISPLAY_NAME") or inst.get("SYMBOL_NAME", ""),
                    "underlying_symbol": inst.get("UNDERLYING_SYMBOL", ""),
                    "instrument_type": inst_type,
                    "exchange": exchange,
                    "segment": segment
                }

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

    For EQUITY instruments: prefers underlying_symbol over symbol_name
    For INDEX/other instruments: uses symbol_name

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

        # Normalize common index queries and detect if it's an index query
        is_index_query = False
        if query_upper in ["NIFTY", "NIFTY 50", "NIFTY50"]:
            query_upper = "NIFTY 50"
            is_index_query = True
        elif query_upper in ["BANK NIFTY", "NIFTY BANK", "BANKNIFTY"]:
            query_upper = "BANK NIFTY"
            is_index_query = True
        elif query_upper in ["SENSEX", "BSE SENSEX"]:
            is_index_query = True

        # Check if this looks like an index query (NIFTY, SENSEX, etc.)
        # Auto-detect common indices even if instrument_type is not specified
        is_index_query = (
            is_index_query or
            (instrument_type and instrument_type.upper() == "INDEX") or
            "NIFTY" in query_upper or
            "SENSEX" in query_upper
        ) or "NIFTY" in query_upper

        # For indices like NIFTY, SENSEX, try to get from IDX_I segment directly first
        if is_index_query:
            try:
                # Try to get instruments from IDX_I segment using API
                segment_result = await trading_service.get_instrument_list_segmentwise("IDX_I")
                if segment_result.get("success") and segment_result.get("data", {}).get("instruments"):
                    idx_instruments = segment_result["data"]["instruments"]
                    matched_instrument = None

                    # Search in IDX_I instruments - filter by underlying_symbol in CAPS
                    for inst in idx_instruments:
                        # Get underlying_symbol in uppercase - this is the key identifier
                        underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or inst.get("UNDERLYING") or "").upper().strip()

                        # Also get other fields for fallback
                        symbol_name = (inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME") or "").upper()
                        trading_symbol = (inst.get("TRADING_SYMBOL") or "").upper()
                        display_name = (inst.get("DISPLAY_NAME") or "").upper()

                        # PRIMARY MATCH: Use underlying_symbol in CAPS to identify the instrument
                        # This is the correct way to identify instruments from the exchange_segment list
                        matches = False
                        if underlying_symbol:
                            # For NIFTY queries, check if underlying_symbol (in CAPS) matches
                            if query_upper == "NIFTY 50" or query_upper == "NIFTY":
                                # Match if underlying_symbol contains "NIFTY" (e.g., "NIFTY", "NIFTY 50")
                                matches = underlying_symbol == "NIFTY" or "NIFTY" in underlying_symbol
                            elif query_upper == "BANK NIFTY":
                                # Match if underlying_symbol contains both "BANK" and "NIFTY"
                                matches = "BANK" in underlying_symbol and "NIFTY" in underlying_symbol
                            else:
                                # Exact match or contains match on underlying_symbol
                                matches = underlying_symbol == query_upper or query_upper in underlying_symbol

                        # FALLBACK: If underlying_symbol doesn't match, check other fields
                        if not matches:
                            if query_upper == "NIFTY 50" or query_upper == "NIFTY":
                                # For NIFTY, match if it contains "NIFTY" and "50" or just "NIFTY 50"
                                matches = ("NIFTY" in symbol_name and "50" in symbol_name) or "NIFTY 50" in symbol_name or "NIFTY 50" in display_name
                            elif query_upper == "BANK NIFTY":
                                matches = "BANK" in symbol_name and "NIFTY" in symbol_name
                            else:
                                matches = (
                                    query_upper in symbol_name or symbol_name == query_upper or
                                    query_upper in trading_symbol or trading_symbol == query_upper or
                                    query_upper in display_name or display_name == query_upper
                                )

                        if matches:
                            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or inst.get("SM_SECURITY_ID")
                            exchange = inst.get("EXCH_ID") or inst.get("SEM_EXM_EXCH_ID") or "NSE"
                            if security_id:
                                matched_instrument = {
                                    "security_id": int(security_id),
                                    "exchange_segment": "IDX_I",
                                    "symbol_name": inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME", ""),
                                    "trading_symbol": inst.get("TRADING_SYMBOL", ""),
                                    "display_name": inst.get("DISPLAY_NAME") or inst.get("SYMBOL_NAME", ""),
                                    "instrument_type": "INDEX",
                                    "exchange": exchange,
                                    "segment": "I"
                                }
                                break  # Found a match, exit loop

                    # If we found a match, return it
                    if matched_instrument:
                        return {
                            "success": True,
                            "data": {
                                "instruments": [matched_instrument],
                                "count": 1,
                                "query": query
                            }
                        }

                    # No match found - return sample instruments for debugging
                    sample_instruments = []
                    for inst in idx_instruments[:20]:  # Show first 20 instruments
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

                    return {
                        "success": False,
                        "error": f"No instruments found matching '{query}'. Found {len(idx_instruments)} total instruments in IDX_I segment.",
                        "data": {
                            "query": query,
                            "total_instruments": len(idx_instruments),
                            "sample_instruments": sample_instruments,
                            "hint": "Check the sample_instruments above to see available instruments. Look for matching underlying_symbol or symbol_name."
                        }
                    }
                elif not segment_result.get("success"):
                    # Log the error but continue to database search
                    error_msg = segment_result.get("error", "Unknown error")
                    print(f"Warning: Failed to fetch IDX_I instruments from API: {error_msg}")
            except Exception as e:
                # Log the error but continue to database search
                print(f"Warning: Exception while fetching IDX_I instruments: {str(e)}")
                import traceback
                print(traceback.format_exc())

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

        # Filter instruments
        results = []
        for inst in instruments:
            # Check various fields
            symbol_name = (inst.get("SYMBOL_NAME") or inst.get("SEM_SYMBOL_NAME") or inst.get("SM_SYMBOL_NAME") or "").upper()
            trading_symbol = (inst.get("SEM_TRADING_SYMBOL") or inst.get("TRADING_SYMBOL") or "").upper()
            display_name = (inst.get("DISPLAY_NAME") or inst.get("SEM_CUSTOM_SYMBOL") or "").upper()
            underlying_symbol = (inst.get("UNDERLYING_SYMBOL") or inst.get("SEM_UNDERLYING_SYMBOL") or "").upper()
            security_id = str(inst.get("SEM_SECURITY_ID") or inst.get("SECURITY_ID") or inst.get("SM_SECURITY_ID") or "")

            # Get segment and exchange for filtering
            segment = (inst.get("SEM_SEGMENT") or inst.get("SEGMENT") or "").upper()
            exchange = (inst.get("SEM_EXM_EXCH_ID") or inst.get("EXCH_ID") or inst.get("EXCHANGE_ID") or "").upper()

            # For index queries, prioritize matching on underlying_symbol (in CAPS) and segment
            if is_index_query:
                # For indices, must have segment "I" and underlying_symbol (in CAPS) should match
                if segment != "I":
                    # Not an index segment, skip for index queries
                    continue

                # PRIMARY MATCH: Check if underlying_symbol (in CAPS) matches
                # This is the key identifier for instruments from exchange_segment list
                matches = False
                if underlying_symbol:
                    # For NIFTY queries, check if underlying_symbol (in CAPS) contains "NIFTY"
                    if query_upper == "NIFTY 50" or query_upper == "NIFTY":
                        # Match if underlying_symbol (in CAPS) equals "NIFTY" or contains "NIFTY"
                        matches = underlying_symbol == "NIFTY" or "NIFTY" in underlying_symbol
                    elif query_upper == "BANK NIFTY":
                        matches = "BANK" in underlying_symbol and "NIFTY" in underlying_symbol
                    else:
                        # Exact match or contains match on underlying_symbol (in CAPS)
                        matches = underlying_symbol == query_upper or query_upper in underlying_symbol

                # FALLBACK: Also check other fields if underlying_symbol doesn't match
                if not matches:
                    matches = (
                        query_upper in symbol_name or
                        query_upper in trading_symbol or
                        query_upper in display_name
                    )

                if not matches:
                    continue
            else:
                # For non-index queries, check all fields
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
                # Handle IDX_I specially
                if exchange_segment == "IDX_I":
                    if segment != "I":
                        continue
                else:
                    expected_exchange = exchange_segment.split("_")[0]
                    expected_segment = exchange_segment.split("_")[1] if "_" in exchange_segment else ""
                    segment_map = {"EQ": "E", "FNO": "D", "FO": "D", "IDX": "I", "COM": "M"}
                    expected_segment_code = segment_map.get(expected_segment, expected_segment)
                    if exchange.upper() != expected_exchange.upper() or (expected_segment_code and segment != expected_segment_code):
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

