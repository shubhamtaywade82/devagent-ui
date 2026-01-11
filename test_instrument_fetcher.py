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
    from tool_executor import find_instrument_by_segment, search_instruments
    from trading import trading_service
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


async def main():
    """Run all tests"""
    parser = argparse.ArgumentParser(description='Test instrument fetcher')
    parser.add_argument('--segment', type=str, help='Exchange segment (e.g., IDX_I, NSE_EQ)')
    parser.add_argument('--symbol', type=str, help='Symbol to search for')
    parser.add_argument('--search', type=str, help='Search query (searches across segments)')
    parser.add_argument('--list', type=str, help='List all instruments from segment (e.g., IDX_I)')
    parser.add_argument('--exact', action='store_true', help='Use exact match')
    parser.add_argument('--case-sensitive', action='store_true', help='Case sensitive search')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Instrument Fetcher Test Suite")
    print("=" * 60)

    # If specific arguments provided, run specific test
    if args.list:
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

