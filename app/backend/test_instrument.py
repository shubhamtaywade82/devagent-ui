#!/usr/bin/env python3
"""
Simple test script for instrument fetcher
Run from the backend directory: python3 test_instrument.py
"""

import asyncio
import argparse
from tool_executor import find_instrument_by_segment, search_instruments
from trading import trading_service


async def test_find(segment, symbol, exact=False, case_sensitive=False):
    """Test find_instrument_by_segment"""
    print(f"\n{'='*60}")
    print(f"Searching for '{symbol}' in segment '{segment}'")
    print(f"{'='*60}")

    result = await find_instrument_by_segment(segment, symbol, exact_match=exact, case_sensitive=case_sensitive)

    if result:
        print(f"✓ FOUND!")
        print(f"  Symbol Name: {result.get('symbol_name')}")
        print(f"  Display Name: {result.get('display_name')}")
        print(f"  Underlying Symbol: {result.get('underlying_symbol')}")
        print(f"  Security ID: {result.get('security_id')}")
        print(f"  Exchange Segment: {result.get('exchange_segment')}")
        print(f"  Instrument Type: {result.get('instrument_type')}")
    else:
        print(f"✗ NOT FOUND")

    return result


async def test_search(query, segment=None, inst_type=None, exact=False, case_sensitive=False):
    """Test search_instruments"""
    print(f"\n{'='*60}")
    print(f"Searching for '{query}'")
    if segment:
        print(f"  Segment: {segment}")
    if inst_type:
        print(f"  Type: {inst_type}")
    print(f"{'='*60}")

    result = await search_instruments(
        query,
        exchange_segment=segment,
        instrument_type=inst_type,
        exact_match=exact,
        case_sensitive=case_sensitive
    )

    if result.get("success"):
        instruments = result.get("data", {}).get("instruments", [])
        print(f"✓ Found {len(instruments)} instrument(s):")
        for inst in instruments:
            print(f"\n  - {inst.get('symbol_name')} / {inst.get('display_name')}")
            print(f"    Security ID: {inst.get('security_id')}")
            print(f"    Exchange Segment: {inst.get('exchange_segment')}")
            print(f"    Underlying Symbol: {inst.get('underlying_symbol')}")
            print(f"    Symbol Name: {inst.get('symbol_name')}")
    else:
        print(f"✗ Error: {result.get('error')}")
        data = result.get("data", {})
        if data and data.get("sample_instruments"):
            print(f"\n  Sample instruments from API (first 10):")
            for sample in data["sample_instruments"][:10]:
                print(f"\n    - Symbol Name: {sample.get('symbol_name')}")
                print(f"      Underlying Symbol: {sample.get('underlying_symbol')}")
                print(f"      Display Name: {sample.get('display_name')}")
                print(f"      Trading Symbol: {sample.get('trading_symbol')}")
                print(f"      Security ID: {sample.get('security_id')}")

    return result


async def test_list(segment="IDX_I", limit=20):
    """List instruments from a segment"""
    print(f"\n{'='*60}")
    print(f"Fetching instruments from segment '{segment}'")
    print(f"{'='*60}")

    result = await trading_service.get_instrument_list_segmentwise(segment)

    if result.get("success"):
        instruments = result.get("data", {}).get("instruments", [])
        print(f"✓ Fetched {len(instruments)} instruments")
        print(f"\nFirst {limit} instruments:")
        for i, inst in enumerate(instruments[:limit], 1):
            symbol_name = inst.get("SYMBOL_NAME") or inst.get("DISPLAY_NAME") or "N/A"
            underlying_symbol = inst.get("UNDERLYING_SYMBOL") or "N/A"
            security_id = inst.get("SECURITY_ID") or inst.get("SEM_SECURITY_ID") or "N/A"
            print(f"\n  {i}. {symbol_name}")
            print(f"     Underlying Symbol: {underlying_symbol}")
            print(f"     Security ID: {security_id}")
            print(f"     Display Name: {inst.get('DISPLAY_NAME', 'N/A')}")
            print(f"     Trading Symbol: {inst.get('TRADING_SYMBOL', 'N/A')}")
    else:
        print(f"✗ Error: {result.get('error')}")

    return result


async def main():
    parser = argparse.ArgumentParser(
        description='Test instrument fetcher functions',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all instruments from IDX_I segment
  python3 test_instrument.py --list IDX_I

  # Find NIFTY in IDX_I segment
  python3 test_instrument.py --find IDX_I NIFTY

  # Search for NIFTY across all segments
  python3 test_instrument.py --search NIFTY

  # Search for NIFTY in IDX_I with exact match
  python3 test_instrument.py --search NIFTY --segment IDX_I --exact
        """
    )

    parser.add_argument('--list', type=str, metavar='SEGMENT',
                       help='List all instruments from segment (e.g., IDX_I, NSE_EQ)')
    parser.add_argument('--find', nargs=2, metavar=('SEGMENT', 'SYMBOL'),
                       help='Find instrument by segment and symbol')
    parser.add_argument('--search', type=str, metavar='QUERY',
                       help='Search for instrument across segments')
    parser.add_argument('--segment', type=str,
                       help='Exchange segment filter (use with --search)')
    parser.add_argument('--type', type=str, choices=['EQUITY', 'INDEX', 'FUTURES', 'OPTIONS'],
                       help='Instrument type filter (use with --search)')
    parser.add_argument('--exact', action='store_true',
                       help='Use exact match')
    parser.add_argument('--case-sensitive', action='store_true',
                       help='Case sensitive search')
    parser.add_argument('--limit', type=int, default=20,
                       help='Limit for list command (default: 20)')

    args = parser.parse_args()

    if args.list:
        await test_list(args.list, args.limit)
    elif args.find:
        segment, symbol = args.find
        await test_find(segment, symbol, args.exact, args.case_sensitive)
    elif args.search:
        await test_search(args.search, args.segment, args.type, args.exact, args.case_sensitive)
    else:
        # Default: run some basic tests
        print("Running default tests...")
        print("\n1. Listing first 10 instruments from IDX_I:")
        await test_list("IDX_I", 10)

        print("\n2. Finding NIFTY in IDX_I:")
        await test_find("IDX_I", "NIFTY")

        print("\n3. Searching for NIFTY:")
        await test_search("NIFTY", inst_type="INDEX")


if __name__ == "__main__":
    asyncio.run(main())

