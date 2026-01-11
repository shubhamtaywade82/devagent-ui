#!/usr/bin/env python3
"""
Test script for instrument fetcher
Tests the find_instrument_by_segment and search_instruments functions

Usage:
    python3 test_instrument_fetcher.py
    python3 test_instrument_fetcher.py --segment IDX_I --symbol NIFTY
    python3 test_instrument_fetcher.py --search NIFTY
"""

import asyncio
import sys
import os
import argparse

# Add the backend directory to the path
backend_path = os.path.join(os.path.dirname(__file__), 'app', 'backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# Change to backend directory to ensure imports work
original_cwd = os.getcwd()
os.chdir(backend_path)

try:
    from tool_executor import find_instrument_by_segment, search_instruments, execute_tool
    from trading import trading_service
    import json
finally:
    os.chdir(original_cwd)


async def test_find_by_segment():
    """Test find_instrument_by_segment function"""
    print("=" * 60)
    print("Testing find_instrument_by_segment")
    print("=" * 60)

    # Test cases
    test_cases = [
        ("IDX_I", "NIFTY", False, False),
        ("IDX_I", "NIFTY 50", False, False),
        ("IDX_I", "BANK NIFTY", False, False),
        ("NSE_EQ", "RELIANCE", False, False),
        ("NSE_EQ", "HDFC", False, False),
    ]

    for exchange_segment, symbol, exact_match, case_sensitive in test_cases:
        print(f"\nSearching for '{symbol}' in segment '{exchange_segment}'...")
        result = await find_instrument_by_segment(
            exchange_segment,
            symbol,
            exact_match=exact_match,
            case_sensitive=case_sensitive
        )

        if result:
            print(f"✓ Found: {result.get('symbol_name')} / {result.get('display_name')}")
            print(f"  Security ID: {result.get('security_id')}")
            print(f"  Exchange Segment: {result.get('exchange_segment')}")
            print(f"  Underlying Symbol: {result.get('underlying_symbol')}")
            print(f"  Instrument Type: {result.get('instrument_type')}")
        else:
            print(f"✗ Not found")


async def test_search_instruments():
    """Test search_instruments function"""
    print("\n" + "=" * 60)
    print("Testing search_instruments")
    print("=" * 60)

    # Test cases
    test_cases = [
        ("NIFTY", None, "INDEX"),
        ("NIFTY 50", None, "INDEX"),
        ("BANK NIFTY", None, "INDEX"),
        ("RELIANCE", None, "EQUITY"),
        ("HDFC", None, "EQUITY"),
        ("NIFTY", "IDX_I", None),
        ("RELIANCE", "NSE_EQ", None),
    ]

    for query, exchange_segment, instrument_type in test_cases:
        print(f"\nSearching for '{query}'...")
        if exchange_segment:
            print(f"  Exchange Segment: {exchange_segment}")
        if instrument_type:
            print(f"  Instrument Type: {instrument_type}")

        result = await search_instruments(
            query,
            exchange_segment=exchange_segment,
            instrument_type=instrument_type,
            limit=5
        )

        if result.get("success"):
            instruments = result.get("data", {}).get("instruments", [])
            print(f"✓ Found {len(instruments)} instrument(s):")
            for inst in instruments:
                print(f"  - {inst.get('symbol_name')} / {inst.get('display_name')}")
                print(f"    Security ID: {inst.get('security_id')}")
                print(f"    Exchange Segment: {inst.get('exchange_segment')}")
                print(f"    Underlying Symbol: {inst.get('underlying_symbol')}")
        else:
            print(f"✗ {result.get('error')}")
            # Show sample instruments if available
            data = result.get("data", {})
            if data and data.get("sample_instruments"):
                print(f"\n  Sample instruments from API:")
                for sample in data["sample_instruments"][:5]:
                    print(f"    - {sample.get('symbol_name')} (symbol_name)")
                    print(f"      {sample.get('underlying_symbol')} (underlying_symbol)")
                    print(f"      {sample.get('display_name')} (display_name)")
                    print(f"      Security ID: {sample.get('security_id')}")


async def test_fetch_segment_instruments(segment="IDX_I"):
    """Test fetching all instruments from a segment"""
    print("\n" + "=" * 60)
    print(f"Testing fetch all instruments from {segment} segment")
    print("=" * 60)

    result = await trading_service.get_instrument_list_segmentwise(segment)

    if result.get("success"):
        instruments = result.get("data", {}).get("instruments", [])
        print(f"\n✓ Fetched {len(instruments)} instruments from IDX_I")
        print("\nFirst 10 instruments:")
        for i, inst in enumerate(instruments[:10], 1):
            symbol_name = inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME") or "N/A"
            underlying_symbol = inst.get("UNDERLYING_SYMBOL") or "N/A"
            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or "N/A"
            print(f"  {i}. {symbol_name}")
            print(f"     Underlying Symbol: {underlying_symbol}")
            print(f"     Security ID: {security_id}")
            print()
    else:
        print(f"✗ Error: {result.get('error')}")


def format_market_quote_result(data, instrument_name=None):
    """Format market quote data for display

    Args:
        data: Market quote data from API
        instrument_name: Optional instrument name to use as fallback if symbol not found in quote data
    """
    if not data:
        return "No market data available"

    formatted = []
    quote_data = None

    if isinstance(data, dict):
        # Check for empty data first
        if "data" in data and isinstance(data["data"], dict):
            if "data" in data["data"]:
                nested_data = data["data"]["data"]
                # Check if nested data is empty
                if isinstance(nested_data, dict) and len(nested_data) == 0:
                    return "No market data available. Possible reasons:\n1. Market is closed\n2. Security ID or exchange segment format is incorrect\n3. For indices like NIFTY, ensure you're using the correct security_id from search_instruments and exchange_segment 'IDX_I'\n\nTry searching for the instrument first using search_instruments to get the correct security_id and exchange_segment."

                # This is the nested structure: data.data.data.{exchange_segment}
                nested = nested_data
                # Iterate through exchange segments (IDX_I, NSE_EQ, NSE_IDX, etc.)
                # Try IDX_I first for indices, then other segments
                for exchange_seg in ["IDX_I", "NSE_IDX", "BSE_IDX", "NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO"]:
                    if exchange_seg in nested:
                        securities = nested[exchange_seg]
                        if isinstance(securities, dict):
                            # Iterate through security IDs
                            for security_id, quote_info in securities.items():
                                if isinstance(quote_info, dict) and quote_info:
                                    quote_data = quote_info
                                    break
                            if quote_data:
                                break

                # If not found in specific segments, try all segments
                if not quote_data:
                    for exchange_seg, securities in nested.items():
                        if isinstance(securities, dict):
                            # Iterate through security IDs
                            for security_id, quote_info in securities.items():
                                if isinstance(quote_info, dict) and quote_info:
                                    quote_data = quote_info
                                    break
                            if quote_data:
                                break
        else:
            # Try direct access - might be flat structure
            quote_data = data

    # Extract quote information with multiple field name variations
    if quote_data and isinstance(quote_data, dict):
        # Try various field name formats from DhanHQ API
        # Check all possible keys for debugging
        all_keys = list(quote_data.keys())

        symbol = (quote_data.get("symbol") or quote_data.get("SYMBOL") or
                 quote_data.get("tradingSymbol") or quote_data.get("TRADING_SYMBOL") or
                 quote_data.get("name") or quote_data.get("NAME") or
                 quote_data.get("instrument_name") or quote_data.get("INSTRUMENT_NAME") or
                 quote_data.get("display_name") or quote_data.get("DISPLAY_NAME") or
                 instrument_name or "N/A")

        # Try multiple variations for LTP
        ltp = None
        for key in ["LTP", "ltp", "lastPrice", "LAST_PRICE", "last_traded_price",
                   "last_price", "LASTPRICE", "CURRENT_PRICE", "current_price", "price"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    ltp = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if ltp is not None:
                        break
                except (ValueError, TypeError):
                    continue
        ltp = ltp if ltp is not None else "N/A"

        # Try multiple variations for OPEN
        open_price = None
        for key in ["OPEN", "open", "openPrice", "OPEN_PRICE", "open_price", "OPENPRICE"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    open_price = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if open_price is not None:
                        break
                except (ValueError, TypeError):
                    continue
        open_price = open_price if open_price is not None else "N/A"

        # Try multiple variations for HIGH
        high = None
        for key in ["HIGH", "high", "highPrice", "HIGH_PRICE", "high_price", "HIGHPRICE"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    high = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if high is not None:
                        break
                except (ValueError, TypeError):
                    continue
        high = high if high is not None else "N/A"

        # Try multiple variations for LOW
        low = None
        for key in ["LOW", "low", "lowPrice", "LOW_PRICE", "low_price", "LOWPRICE"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    low = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if low is not None:
                        break
                except (ValueError, TypeError):
                    continue
        low = low if low is not None else "N/A"

        # Try multiple variations for CLOSE
        close = None
        for key in ["CLOSE", "close", "closePrice", "CLOSE_PRICE", "close_price",
                   "previousClose", "PREV_CLOSE", "prev_close", "PREVIOUS_CLOSE", "previous_close"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    close = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if close is not None:
                        break
                except (ValueError, TypeError):
                    continue
        close = close if close is not None else "N/A"

        # Try multiple variations for VOLUME
        volume = None
        for key in ["VOLUME", "volume", "totalVolume", "TOTAL_VOLUME", "total_volume",
                   "VOL", "vol", "TURNOVER", "turnover"]:
            val = quote_data.get(key)
            if val is not None and val != "":
                try:
                    volume = float(val) if isinstance(val, (int, float, str)) and str(val).strip() else None
                    if volume is not None:
                        break
                except (ValueError, TypeError):
                    continue
        volume = volume if volume is not None else "N/A"

        # Format the output
        formatted.append(f"""
Symbol: {symbol}
Current Price (LTP): ₹{ltp}
Open: ₹{open_price}
High: ₹{high}
Low: ₹{low}
Previous Close: ₹{close}
Volume: {volume}
""")

        # Add debug info if all values are N/A
        if (ltp == "N/A" and open_price == "N/A" and high == "N/A" and
            low == "N/A" and close == "N/A" and volume == "N/A"):
            formatted.append(f"\n⚠ Debug: All values are N/A. Available keys in quote_data: {all_keys}")
            formatted.append(f"   Sample values: {dict(list(quote_data.items())[:10])}")

    # If we couldn't find the data, return the raw structure for debugging
    if not formatted:
        # Try to extract any numeric values that might be prices
        if isinstance(data, dict):
            # Look for any numeric fields that might be prices
            for key, value in data.items():
                if isinstance(value, (int, float)) and value > 0:
                    formatted.append(f"{key}: {value}")

        if not formatted:
            # Last resort: return formatted JSON
            return f"Market data received but format not recognized. Raw data:\n{json.dumps(data, indent=2)}"

    return "\n".join(formatted) if formatted else "No market data available"


async def test_fetch_market_quote(symbol_query, access_token=None):
    """Test fetching market quote for a symbol"""
    print("\n" + "=" * 60)
    print(f"Testing market quote fetch for '{symbol_query}'")
    print("=" * 60)

    if not access_token:
        print("⚠ Warning: No access token provided. Market quote requires authentication.")
        print("   You can provide it via --token argument or DHAN_ACCESS_TOKEN environment variable.")
        return

    # First, search for the instrument
    print(f"\nStep 1: Searching for instrument '{symbol_query}'...")

    # Determine if this is an index search
    is_index = any(keyword in symbol_query.upper() for keyword in ["NIFTY", "SENSEX", "INDEX"])

    result = await search_instruments(
        symbol_query,
        instrument_type="INDEX" if is_index else None,
        limit=10  # Get more results to find the right match
    )

    if not result.get("success"):
        print(f"✗ Failed to search instruments: {result.get('error')}")
        return

    instruments = result.get("data", {}).get("instruments", [])
    if not instruments:
        print(f"✗ No instruments found for '{symbol_query}'")
        return

    # Show all found instruments with all relevant fields
    print(f"✓ Found {len(instruments)} instrument(s):")
    for i, inst in enumerate(instruments, 1):
        underlying = inst.get("underlying_symbol") or "N/A"
        symbol_name = inst.get("symbol_name") or "N/A"
        display_name = inst.get("display_name") or "N/A"
        inst_id = inst.get("security_id")
        inst_seg = inst.get("exchange_segment")
        print(f"  {i}. Underlying: {underlying} | Symbol: {symbol_name} | Display: {display_name}")
        print(f"     Security ID: {inst_id}, Segment: {inst_seg}")

    # Try to find exact or best match
    # Priority: 1. underlying_symbol, 2. symbol_name, 3. display_name
    instrument = None
    symbol_upper = symbol_query.upper()

    # First, try exact match with underlying_symbol (highest priority)
    for inst in instruments:
        underlying = (inst.get("underlying_symbol") or "").upper()
        if underlying and (symbol_upper in underlying or underlying in symbol_upper):
            instrument = inst
            match_type = "underlying_symbol"
            match_value = inst.get("underlying_symbol")
            break

    # If no match with underlying_symbol, try symbol_name
    if not instrument:
        for inst in instruments:
            symbol_name = (inst.get("symbol_name") or "").upper()
            if symbol_name and (symbol_upper in symbol_name or symbol_name in symbol_upper):
                instrument = inst
                match_type = "symbol_name"
                match_value = inst.get("symbol_name")
                break

    # If still no match, try display_name
    if not instrument:
        for inst in instruments:
            display_name = (inst.get("display_name") or "").upper()
            if display_name and (symbol_upper in display_name or display_name in symbol_upper):
                instrument = inst
                match_type = "display_name"
                match_value = inst.get("display_name")
                break

    # If no match found, use the first one
    if not instrument:
        instrument = instruments[0]
        print(f"\n⚠ No match found in underlying_symbol/symbol_name/display_name, using first result")
    else:
        print(f"\n✓ Found best match by {match_type}: {match_value}")

    security_id = instrument.get("security_id")
    exchange_segment = instrument.get("exchange_segment")
    # Use priority order: underlying_symbol > symbol_name > display_name
    symbol_name = (instrument.get("underlying_symbol") or
                  instrument.get("symbol_name") or
                  instrument.get("display_name") or "N/A")

    print(f"\n✓ Using instrument: {symbol_name}")
    print(f"  Security ID: {security_id}")
    print(f"  Exchange Segment: {exchange_segment}")
    print(f"  Underlying Symbol: {instrument.get('underlying_symbol') or 'N/A'}")
    print(f"  Symbol Name: {instrument.get('symbol_name') or 'N/A'}")
    print(f"  Display Name: {instrument.get('display_name') or 'N/A'}")

    # Now fetch the market quote
    print(f"\nStep 2: Fetching market quote...")
    try:
        quote_result = await execute_tool(
            "get_market_quote",
            {
                "securities": {
                    exchange_segment: [int(security_id)]
                }
            },
            access_token
        )

        if quote_result.get("success"):
            print("✓ Market quote fetched successfully")
            print("\n" + "=" * 60)
            # Use the best available name for the quote display (priority order)
            quote_instrument_name = (instrument.get("underlying_symbol") or
                                   instrument.get("symbol_name") or
                                   instrument.get("display_name"))
            formatted = format_market_quote_result(quote_result.get("data", {}), instrument_name=quote_instrument_name)
            print(formatted)
            print("=" * 60)

            # Also print raw data for debugging
            print("\nRaw response structure (for debugging):")
            print(json.dumps(quote_result.get("data", {}), indent=2, default=str))
        else:
            print(f"✗ Failed to fetch market quote: {quote_result.get('error')}")
    except Exception as e:
        print(f"✗ Error fetching market quote: {str(e)}")
        import traceback
        traceback.print_exc()


async def main():
    """Run all tests"""
    parser = argparse.ArgumentParser(description='Test instrument fetcher')
    parser.add_argument('--segment', type=str, help='Exchange segment (e.g., IDX_I, NSE_EQ)')
    parser.add_argument('--symbol', type=str, help='Symbol to search for')
    parser.add_argument('--search', type=str, help='Search query (searches across segments)')
    parser.add_argument('--list', type=str, help='List all instruments from segment (e.g., IDX_I)')
    parser.add_argument('--quote', type=str, help='Fetch market quote for a symbol (e.g., NIFTY, RELIANCE)')
    parser.add_argument('--token', type=str, help='DhanHQ access token (or set DHAN_ACCESS_TOKEN env var)')
    parser.add_argument('--exact', action='store_true', help='Use exact match')
    parser.add_argument('--case-sensitive', action='store_true', help='Case sensitive search')

    args = parser.parse_args()

    # Get access token from args or environment
    access_token = args.token or os.environ.get("DHAN_ACCESS_TOKEN")

    print("\n" + "=" * 60)
    print("Instrument Fetcher Test Suite")
    print("=" * 60)

    # If specific arguments provided, run specific test
    if args.quote:
        await test_fetch_market_quote(args.quote, access_token)
    elif args.list:
        await test_fetch_segment_instruments(args.list)
    elif args.segment and args.symbol:
        print(f"\nSearching for '{args.symbol}' in segment '{args.segment}'...")
        result = await find_instrument_by_segment(
            args.segment,
            args.symbol,
            exact_match=args.exact,
            case_sensitive=args.case_sensitive
        )
        if result:
            print(f"✓ Found: {result.get('symbol_name')} / {result.get('display_name')}")
            print(f"  Security ID: {result.get('security_id')}")
            print(f"  Exchange Segment: {result.get('exchange_segment')}")
            print(f"  Underlying Symbol: {result.get('underlying_symbol')}")
            print(f"  Symbol Name: {result.get('symbol_name')}")
            print(f"  Instrument Type: {result.get('instrument_type')}")
        else:
            print(f"✗ Not found")
    elif args.search:
        print(f"\nSearching for '{args.search}'...")
        result = await search_instruments(
            args.search,
            exact_match=args.exact,
            case_sensitive=args.case_sensitive
        )
        if result.get("success"):
            instruments = result.get("data", {}).get("instruments", [])
            print(f"✓ Found {len(instruments)} instrument(s):")
            for inst in instruments:
                print(f"  - {inst.get('symbol_name')} / {inst.get('display_name')}")
                print(f"    Security ID: {inst.get('security_id')}")
                print(f"    Exchange Segment: {inst.get('exchange_segment')}")
                print(f"    Underlying Symbol: {inst.get('underlying_symbol')}")
        else:
            print(f"✗ {result.get('error')}")
            data = result.get("data", {})
            if data and data.get("sample_instruments"):
                print(f"\n  Sample instruments from API:")
                for sample in data["sample_instruments"][:10]:
                    print(f"    - {sample.get('symbol_name')} (symbol_name)")
                    print(f"      {sample.get('underlying_symbol')} (underlying_symbol)")
                    print(f"      {sample.get('display_name')} (display_name)")
                    print(f"      Security ID: {sample.get('security_id')}")
    else:
        # Run all tests
        # Test 1: Fetch all instruments from segment
        await test_fetch_segment_instruments()

        # Test 2: Find by segment
        await test_find_by_segment()

        # Test 3: Search instruments
        await test_search_instruments()

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

