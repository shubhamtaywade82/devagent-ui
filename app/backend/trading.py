"""
Trading module for DhanHQ integration
"""
from dhanhq import dhanhq  # type: ignore
from typing import Optional, Dict, List, Any, Callable
import os
import httpx  # pyright: ignore[reportMissingImports]
import asyncio
import json
import csv
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv  # pyright: ignore[reportMissingImports]

load_dotenv()

class TradingService:
    """Service for managing DhanHQ trading operations"""

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        self.app_id = os.getenv("DHAN_APP_ID")
        self.app_secret = os.getenv("DHAN_APP_SECRET")
        self.dhan = None

    def get_dhan_instance(self, access_token: str):
        """Get or create DhanHQ instance with access token"""
        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID is not configured in backend environment. Please set it in app/backend/.env file.")
        # Always create a new instance to ensure correct access token
        # The dhanhq library doesn't expose access_token for comparison
        return dhanhq(self.client_id, access_token)

    def authenticate_with_pin(self, pin: str, totp: str) -> Dict[str, Any]:
        """Authenticate using PIN and TOTP - requires external API call"""
        try:
            # PIN/TOTP authentication requires calling DhanHQ API directly
            # This is not available in the dhanhq library v2.0.2
            # Users should generate tokens via DhanHQ web portal
            return {
                "success": False,
                "error": "PIN/TOTP authentication not available in this version. Please generate access token from DhanHQ web portal."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def authenticate_oauth(self, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Generate OAuth consent URL - requires external API call"""
        try:
            # OAuth requires calling DhanHQ API directly
            # This is not available in the dhanhq library v2.0.2
            return {
                "success": False,
                "error": "OAuth authentication not available in this version. Please generate access token from DhanHQ web portal."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def consume_token_id(self, token_id: str, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Consume token ID from OAuth redirect - requires external API call"""
        try:
            # Token consumption requires calling DhanHQ API directly
            return {
                "success": False,
                "error": "OAuth token consumption not available in this version. Please generate access token from DhanHQ web portal."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information by validating token"""
        try:
            if not self.client_id:
                return {"success": False, "error": "DHAN_CLIENT_ID not configured in backend"}

            # Validate token by creating a dhanhq instance and making a simple API call
            dhan = self.get_dhan_instance(access_token)
            # Try to get fund limits as a way to validate the token
            funds = dhan.get_fund_limits()
            return {
                "success": True,
                "data": {
                    "access_token_valid": True,
                    "client_id": self.client_id
                }
            }
        except ValueError as e:
            # This is likely a configuration error
            return {"success": False, "error": str(e)}
        except Exception as e:
            # Log the full error for debugging
            error_msg = str(e)
            # Check if it's an API error from DhanHQ
            if "401" in error_msg or "Unauthorized" in error_msg or "Invalid" in error_msg:
                return {"success": False, "error": "Invalid or expired access token. Please generate a new token from DhanHQ web portal."}
            return {"success": False, "error": f"Token validation failed: {error_msg}"}

    def place_order(self, access_token: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place a trading order"""
        try:
            dhan = self.get_dhan_instance(access_token)

            result = dhan.place_order(
                security_id=order_data["security_id"],
                exchange_segment=getattr(dhan, order_data["exchange_segment"]),
                transaction_type=getattr(dhan, order_data["transaction_type"]),
                quantity=order_data["quantity"],
                order_type=getattr(dhan, order_data["order_type"]),
                product_type=getattr(dhan, order_data["product_type"]),
                price=order_data.get("price", 0),
                trigger_price=order_data.get("trigger_price", 0),
                disclosed_quantity=order_data.get("disclosed_quantity", 0),
                validity=order_data.get("validity", "DAY")
            )
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_orders(self, access_token: str) -> Dict[str, Any]:
        """Get all orders"""
        try:
            dhan = self.get_dhan_instance(access_token)
            orders = dhan.get_order_list()
            return {"success": True, "data": orders}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_order_by_id(self, access_token: str, order_id: str) -> Dict[str, Any]:
        """Get order by ID"""
        try:
            dhan = self.get_dhan_instance(access_token)
            order = dhan.get_order_by_id(order_id)
            return {"success": True, "data": order}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_order(self, access_token: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            dhan = self.get_dhan_instance(access_token)
            result = dhan.cancel_order(order_id)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def modify_order(self, access_token: str, order_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an order"""
        try:
            dhan = self.get_dhan_instance(access_token)
            result = dhan.modify_order(
                order_id,
                order_data.get("order_type"),
                order_data.get("leg_name"),
                order_data.get("quantity"),
                order_data.get("price"),
                order_data.get("trigger_price"),
                order_data.get("disclosed_quantity"),
                order_data.get("validity")
            )
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_positions(self, access_token: str) -> Dict[str, Any]:
        """Get current positions"""
        try:
            dhan = self.get_dhan_instance(access_token)
            positions = dhan.get_positions()
            return {"success": True, "data": positions}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_holdings(self, access_token: str) -> Dict[str, Any]:
        """Get current holdings"""
        try:
            dhan = self.get_dhan_instance(access_token)
            holdings = dhan.get_holdings()
            return {"success": True, "data": holdings}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_fund_limits(self, access_token: str) -> Dict[str, Any]:
        """Get fund limits and margin details"""
        try:
            dhan = self.get_dhan_instance(access_token)
            funds = dhan.get_fund_limits()
            return {"success": True, "data": funds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_market_quote(self, access_token: str, securities: Dict[str, List[int]]) -> Dict[str, Any]:
        """Get market quote data"""
        try:
            dhan = self.get_dhan_instance(access_token)

            # Convert string security IDs to integers if needed (ohlc_data expects integers)
            securities_int = {}
            for exchange_seg, sec_ids in securities.items():
                securities_int[exchange_seg] = [
                    int(sec_id) if isinstance(sec_id, str) else sec_id
                    for sec_id in sec_ids
                ]

            print(f"[get_market_quote] Calling ohlc_data with securities (original): {securities}")
            print(f"[get_market_quote] Calling ohlc_data with securities (converted to int): {securities_int}")
            quote = dhan.ohlc_data(securities=securities_int)

            # Log the response structure for debugging
            print(f"[get_market_quote] Response type: {type(quote)}")
            if isinstance(quote, dict):
                print(f"[get_market_quote] Response keys: {list(quote.keys())}")
                # Log nested structure if present
                if "data" in quote:
                    print(f"[get_market_quote] data keys: {list(quote['data'].keys()) if isinstance(quote['data'], dict) else type(quote['data'])}")
                    if isinstance(quote['data'], dict) and "data" in quote['data']:
                        nested = quote['data']['data']
                        if isinstance(nested, dict):
                            print(f"[get_market_quote] nested data keys: {list(nested.keys())}")
                            for key in nested.keys():
                                if isinstance(nested[key], dict):
                                    print(f"[get_market_quote]   {key} has {len(nested[key])} securities: {list(nested[key].keys())[:5]}")
            elif isinstance(quote, list):
                print(f"[get_market_quote] Response is list with {len(quote)} items")
            else:
                print(f"[get_market_quote] Response: {str(quote)[:500]}")

            return {"success": True, "data": quote}
        except Exception as e:
            print(f"[get_market_quote] Exception: {str(e)}")
            import traceback
            print(f"[get_market_quote] Traceback: {traceback.format_exc()}")
            return {"success": False, "error": str(e)}

    def get_option_chain(self, access_token: str, under_security_id: int,
                        under_exchange_segment: str, expiry: str) -> Dict[str, Any]:
        """Get option chain data"""
        try:
            dhan = self.get_dhan_instance(access_token)
            chain = dhan.option_chain(
                under_security_id=under_security_id,
                under_exchange_segment=under_exchange_segment,
                expiry=expiry
            )
            return {"success": True, "data": chain}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_historical_data(self, access_token: str, security_id: int,
                           exchange_segment: str, instrument_type: str,
                           from_date: str, to_date: str, interval: str) -> Dict[str, Any]:
        """
        Get historical data (daily or intraday minute data)

        Per official example: Uses DhanContext, string security_id, and dhan exchange constants

        Args:
            access_token: DhanHQ access token
            security_id: Security ID (will be converted to string per official example)
            exchange_segment: Exchange segment string (e.g., "NSE_EQ", "BSE_EQ") or constant
            instrument_type: Instrument type (e.g., "EQUITY", "FUTURES", "OPTIONS")
            from_date: Start date in "YYYY-MM-DD" format
            to_date: End date in "YYYY-MM-DD" format
            interval: "daily" for daily data, "intraday" or "minute" for intraday minute data

        Returns:
            Dict with success status and data or error message
        """
        try:
            # Import DhanContext if available (per official example pattern)
            try:
                from dhanhq import DhanContext
                use_dhan_context = True
            except ImportError:
                use_dhan_context = False

            # Get dhan instance
            if use_dhan_context:
                dhan_context = DhanContext(self.client_id, access_token)
                from dhanhq import dhanhq
                dhan = dhanhq(dhan_context)
            else:
                dhan = self.get_dhan_instance(access_token)

            # Convert security_id to string (per official example: "1333" not 1333)
            # Also ensure we have the numeric value for comparisons
            security_id_int = int(security_id) if isinstance(security_id, str) else security_id
            security_id_str = str(security_id_int)

            # For historical data API, exchange_segment should be just the exchange name (NSE, BSE, MCX, NCDEX)
            # Not the full segment like "NSE_EQ" or "IDX_I"
            # Extract base exchange from exchange_segment
            exchange_seg_str = exchange_segment.upper()

            # Handle IDX_I (indices): DhanHQ historical endpoints typically require base exchange (NSE/BSE).
            # We do NOT hardcode security IDs to infer exchange. Instead, we try NSE first, and if it fails,
            # the existing fallback logic below will try BSE.
            if exchange_seg_str == "IDX_I":
                print(f"[get_historical_data] Processing IDX_I index with security_id={security_id_int} (trying NSE with BSE fallback)")
                exchange_seg_str = "NSE"
            elif exchange_seg_str.startswith('NSE'):
                # Extract "NSE" from "NSE_EQ", "NSE_FO", etc.
                exchange_seg_str = "NSE"
            elif exchange_seg_str.startswith('BSE'):
                # Extract "BSE" from "BSE_EQ", "BSE_FO", etc.
                exchange_seg_str = "BSE"
            elif exchange_seg_str.startswith('MCX'):
                # Extract "MCX" from "MCX_COM", etc.
                exchange_seg_str = "MCX"
            elif exchange_seg_str.startswith('NCDEX'):
                # Extract "NCDEX" from "NCDEX_COM", etc.
                exchange_seg_str = "NCDEX"

            # Map exchange string to dhan constant if possible
            # Official example uses: dhan.NSE, dhan.BSE, etc.
            # But we can also pass the string directly if constant not available
            exchange_constant = None
            if hasattr(dhan, 'NSE') and exchange_seg_str == 'NSE':
                exchange_constant = dhan.NSE
            elif hasattr(dhan, 'BSE') and exchange_seg_str == 'BSE':
                exchange_constant = dhan.BSE
            elif hasattr(dhan, 'MCX') and exchange_seg_str == 'MCX':
                exchange_constant = dhan.MCX
            elif hasattr(dhan, 'NCDEX') and exchange_seg_str == 'NCDEX':
                exchange_constant = dhan.NCDEX

            # Use constant if available, otherwise use the base exchange string
            # According to docs, exchange_segment should be like "NSE", "BSE" (string or constant)
            exchange_seg = exchange_constant if exchange_constant is not None else exchange_seg_str

            # Fetch data based on interval type
            try:
                # Check if interval is numeric (1, 5, 10, 15, 60) or daily
                interval_str = str(interval).strip()
                is_daily = interval_str.lower() in ["daily", "day"]

                if is_daily:
                    # Daily historical data (per official example)
                    print(f"[get_historical_data] Calling historical_daily_data with security_id={security_id_str}, exchange_seg={exchange_seg}, instrument_type={instrument_type}, from_date={from_date}, to_date={to_date}")
                    data = dhan.historical_daily_data(
                        security_id=security_id_str,
                        exchange_segment=exchange_seg,
                        instrument_type=instrument_type,
                        from_date=from_date,
                        to_date=to_date
                    )
                else:
                    # Intraday minute data using REST API /v2/charts/intraday
                    # This endpoint supports intervals: 1, 5, 15, 25, 60
                    # Requires exchangeSegment (e.g., "NSE_EQ") not just "NSE"
                    # Requires instrument (e.g., "EQUITY") not instrument_type
                    # Date format: "YYYY-MM-DD HH:MM:SS"

                    # Enforce strict intraday interval (no silent defaults).
                    if not interval_str.isdigit():
                        return {
                            "success": False,
                            "error": f"Invalid interval '{interval_str}'. Must be one of: 1, 5, 15, 25, 60."
                        }
                    interval_int = int(interval_str)
                    if interval_int not in [1, 5, 15, 25, 60]:
                        return {
                            "success": False,
                            "error": f"Invalid interval '{interval_int}'. Must be one of: 1, 5, 15, 25, 60."
                        }
                    interval_value = str(interval_int)

                    # Use original exchange_segment (e.g., "NSE_EQ", "IDX_I") for REST API
                    # Convert instrument_type to instrument
                    instrument = instrument_type.upper()

                    # Format dates with time: "YYYY-MM-DD HH:MM:SS"
                    # Market hours: 9:15 AM to 3:30 PM IST
                    from_datetime = f"{from_date} 09:15:00"
                    to_datetime = f"{to_date} 15:30:00"

                    print(f"[get_historical_data] Calling REST API /v2/charts/intraday with:")
                    print(f"  securityId={security_id_str}")
                    print(f"  exchangeSegment={exchange_segment}")
                    print(f"  instrument={instrument}")
                    print(f"  interval={interval_value}")
                    print(f"  fromDate={from_datetime}")
                    print(f"  toDate={to_datetime}")

                    # Call REST API endpoint
                    api_url = "https://api.dhan.co/v2/charts/intraday"
                    headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "access-token": access_token
                    }
                    payload = {
                        "securityId": security_id_str,
                        "exchangeSegment": exchange_segment,  # Use original format like "NSE_EQ", "IDX_I"
                        "instrument": instrument,
                        "interval": interval_value,
                        "oi": False,  # Open Interest (for F&O)
                        "fromDate": from_datetime,
                        "toDate": to_datetime
                    }

                    try:
                        response = httpx.post(api_url, headers=headers, json=payload, timeout=30.0)
                        response.raise_for_status()
                        data = response.json()

                        # Transform response from arrays to list of objects for easier processing
                        if isinstance(data, dict) and "open" in data and "close" in data:
                            # Convert array format to list of candle objects
                            opens = data.get("open", [])
                            highs = data.get("high", [])
                            lows = data.get("low", [])
                            closes = data.get("close", [])
                            volumes = data.get("volume", [])
                            timestamps = data.get("timestamp", [])
                            oi = data.get("open_interest", [])

                            candles = []
                            for i in range(len(opens)):
                                candle = {
                                    "timestamp": timestamps[i] if i < len(timestamps) else None,
                                    "time": datetime.fromtimestamp(timestamps[i]).isoformat() if i < len(timestamps) and timestamps[i] else None,
                                    "date": datetime.fromtimestamp(timestamps[i]).isoformat() if i < len(timestamps) and timestamps[i] else None,
                                    "open": opens[i] if i < len(opens) else None,
                                    "high": highs[i] if i < len(highs) else None,
                                    "low": lows[i] if i < len(lows) else None,
                                    "close": closes[i] if i < len(closes) else None,
                                    "volume": volumes[i] if i < len(volumes) else 0,
                                    "open_interest": oi[i] if i < len(oi) else 0
                                }
                                candles.append(candle)

                            data = candles
                            print(f"[get_historical_data] Transformed {len(candles)} candles from REST API response")
                        else:
                            print(f"[get_historical_data] Unexpected REST API response format")

                    except httpx.HTTPStatusError as e:
                        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
                        print(f"[get_historical_data] REST API HTTP error: {error_msg}")
                        # Try to parse error response
                        try:
                            error_data = e.response.json()
                            if isinstance(error_data, dict) and ("status" in error_data or "error" in error_data):
                                raise Exception(error_msg)
                        except:
                            pass
                        raise Exception(error_msg)
                    except Exception as e:
                        error_msg = str(e)
                        print(f"[get_historical_data] REST API call failed: {error_msg}")
                        raise

                print(f"[get_historical_data] Success - data type: {type(data)}, length: {len(data) if isinstance(data, (list, dict)) else 'N/A'}")

                # Check if the response is an error response from DhanHQ
                if isinstance(data, dict):
                    # Check for DhanHQ error structure
                    if data.get("status") == "failure" or "error" in data or "errorCode" in data:
                        error_info = data.get("remarks") or data.get("data") or data
                        error_code = error_info.get("error_code") or error_info.get("errorCode") or ""
                        error_message = error_info.get("error_message") or error_info.get("errorMessage") or str(error_info)
                        error_msg = f"DhanHQ Error {error_code}: {error_message}" if error_code else error_message
                        print(f"[get_historical_data] DhanHQ API returned error: {error_msg}")
                        return {"success": False, "error": error_msg, "error_code": error_code, "raw_response": data}

                return {"success": True, "data": data}
            except Exception as api_error:
                error_msg = str(api_error)
                print(f"[get_historical_data] API call failed: {error_msg}")

                # Try to extract error details from exception
                if hasattr(api_error, 'response') or hasattr(api_error, 'args'):
                    error_details = getattr(api_error, 'args', [])
                    if error_details and isinstance(error_details[0], dict):
                        error_data = error_details[0]
                        if error_data.get("status") == "failure":
                            error_info = error_data.get("remarks") or error_data.get("data") or {}
                            error_code = error_info.get("error_code") or error_info.get("errorCode") or ""
                            error_message = error_info.get("error_message") or error_info.get("errorMessage") or str(error_info)
                            error_msg = f"DhanHQ Error {error_code}: {error_message}" if error_code else error_message
                            return {"success": False, "error": error_msg, "error_code": error_code, "raw_response": error_data}

                # For indices (when original exchange_segment was IDX_I), try fallback to other exchange if first attempt failed
                if exchange_segment.upper() == "IDX_I" and hasattr(dhan, 'NSE') and hasattr(dhan, 'BSE'):
                    # Try the other exchange as fallback
                    # If we tried NSE first, try BSE, and vice versa
                    if exchange_seg_str == "NSE":
                        fallback_exchange = dhan.BSE
                        fallback_name = "BSE"
                    elif exchange_seg_str == "BSE":
                        fallback_exchange = dhan.NSE
                        fallback_name = "NSE"
                    else:
                        fallback_exchange = None

                    if fallback_exchange:
                        print(f"[get_historical_data] Trying fallback exchange: {fallback_name}")
                        try:
                            interval_str = str(interval).strip()
                            is_daily = interval_str.lower() in ["daily", "day"]

                            if is_daily:
                                data = dhan.historical_daily_data(
                                    security_id=security_id_str,
                                    exchange_segment=fallback_exchange,
                                    instrument_type=instrument_type,
                                    from_date=from_date,
                                    to_date=to_date
                                )
                            else:
                                # Handle interval for fallback call - use numeric interval
                                if not interval_str.isdigit():
                                    return {
                                        "success": False,
                                        "error": f"Invalid interval '{interval_str}'. Must be one of: 1, 5, 15, 25, 60."
                                    }
                                fallback_interval = int(interval_str)
                                if fallback_interval not in [1, 5, 15, 25, 60]:
                                    return {
                                        "success": False,
                                        "error": f"Invalid interval '{fallback_interval}'. Must be one of: 1, 5, 15, 25, 60."
                                    }

                                data = dhan.intraday_minute_data(
                                    security_id=security_id_str,
                                    exchange_segment=fallback_exchange,
                                    instrument_type=instrument_type,
                                    from_date=from_date,
                                    to_date=to_date,
                                    interval=fallback_interval
                                )
                            print(f"[get_historical_data] Fallback succeeded with {fallback_name}")
                            return {"success": True, "data": data}
                        except Exception as fallback_error:
                            print(f"[get_historical_data] Fallback also failed: {str(fallback_error)}")
                            return {"success": False, "error": f"Original error: {error_msg}. Fallback error: {str(fallback_error)}"}

                return {"success": False, "error": error_msg}
        except Exception as e:
            print(f"[get_historical_data] Outer exception: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_security_list(self, access_token: str, format_type: str = "compact") -> Dict[str, Any]:
        """Get security/instrument list"""
        try:
            dhan = self.get_dhan_instance(access_token)
            securities = dhan.fetch_security_list(format_type)
            return {"success": True, "data": securities}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_expiry_list(self, access_token: str, under_security_id: int,
                       under_exchange_segment: str) -> Dict[str, Any]:
        """Get expiry list for underlying"""
        try:
            dhan = self.get_dhan_instance(access_token)
            expiries = dhan.expiry_list(
                under_security_id=under_security_id,
                under_exchange_segment=under_exchange_segment
            )
            return {"success": True, "data": expiries}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_trades(self, access_token: str) -> Dict[str, Any]:
        """Get all trades executed today"""
        try:
            dhan = self.get_dhan_instance(access_token)
            trades = dhan.get_trade_book()
            return {"success": True, "data": trades}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_trade_by_order_id(self, access_token: str, order_id: str) -> Dict[str, Any]:
        """Get trades by order ID"""
        try:
            dhan = self.get_dhan_instance(access_token)
            trades = dhan.get_trade_by_order_id(order_id)
            return {"success": True, "data": trades}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_trade_history(self, access_token: str, from_date: str, to_date: str, page_number: int = 0) -> Dict[str, Any]:
        """Get trade history for date range"""
        try:
            dhan = self.get_dhan_instance(access_token)
            trades = dhan.get_trade_history(from_date, to_date, page_number)
            return {"success": True, "data": trades}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def calculate_margin(self, access_token: str, margin_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate margin for an order"""
        try:
            dhan = self.get_dhan_instance(access_token)
            margin = dhan.margin_calculator(
                security_id=margin_data.get("security_id"),
                exchange_segment=getattr(dhan, margin_data.get("exchange_segment", "NSE_EQ")),
                transaction_type=getattr(dhan, margin_data.get("transaction_type", "BUY")),
                quantity=margin_data.get("quantity", 1),
                product_type=getattr(dhan, margin_data.get("product_type", "INTRADAY")),
                price=margin_data.get("price", 0),
                trigger_price=margin_data.get("trigger_price", 0)
            )
            return {"success": True, "data": margin}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_kill_switch_status(self, access_token: str) -> Dict[str, Any]:
        """Get kill switch status"""
        try:
            dhan = self.get_dhan_instance(access_token)
            status = dhan.kill_switch()
            return {"success": True, "data": status}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def manage_kill_switch(self, access_token: str, status: str) -> Dict[str, Any]:
        """Manage kill switch (ACTIVATE or DEACTIVATE)"""
        try:
            dhan = self.get_dhan_instance(access_token)
            result = dhan.kill_switch(status)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_ledger(self, access_token: str, from_date: Optional[str] = None, to_date: Optional[str] = None) -> Dict[str, Any]:
        """Get ledger report"""
        try:
            dhan = self.get_dhan_instance(access_token)
            ledger = dhan.ledger_report(from_date, to_date)
            return {"success": True, "data": ledger}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_market_feed(self, access_token: str, instruments: List[tuple], version: str = "v2"):
        """
        Create Market Feed instance for real-time data

        Args:
            access_token: DhanHQ access token
            instruments: List of tuples in format [(exchange_code, security_id, feed_request_code), ...]
                       exchange_code: 1=NSE, 2=BSE, etc. (numeric codes are supported)
                       security_id: Security ID (will be converted to string per official example)
                       feed_request_code: 1=Ticker, 2=Quote, 3=Full, 4=Market Depth, 5=OI, 6=Previous Day
            version: API version ('v1' or 'v2', default 'v2' per official recommendation)

        Returns:
            DhanFeed instance (MarketFeed class from dhanhq library)
        """
        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID is not configured")
        try:
            # Import DhanFeed and constants (actual class name in dhanhq library)
            from dhanhq.marketfeed import DhanFeed, Ticker, Quote, Full, NSE, BSE, IDX

            # Convert instruments to use proper constants
            # For v2, use RequestCode values directly: Ticker=15, Quote=17, Full=21
            # Map numeric feed codes to constants
            feed_code_to_constant = {
                1: Ticker,   # Ticker Packet (RequestCode 15)
                2: Quote,    # Quote Packet (RequestCode 17)
                3: Full,     # Full Packet (RequestCode 21)
                15: Ticker,  # Direct RequestCode mapping
                17: Quote,
                21: Full,
            }

            # Map exchange codes to constants
            exchange_code_to_constant = {
                0: IDX,   # Index (IDX = 0)
                1: NSE,   # NSE (NSE = 1)
                2: BSE,   # BSE (BSE = 2)
            }

            # Note: IDX, NSE, BSE are just integers (0, 1, 2), so mapping is optional
            # But we keep it for clarity and consistency

            converted_instruments = []
            for inst in instruments:
                if len(inst) >= 3:
                    exchange_code, security_id, feed_code = inst[0], inst[1], inst[2]
                    # Convert security_id to string
                    security_id_str = str(security_id) if not isinstance(security_id, str) else security_id

                    # Convert exchange_code to constant if available
                    exchange_constant = exchange_code_to_constant.get(exchange_code, exchange_code)

                    # Convert feed_code to constant (RequestCode value)
                    feed_constant = feed_code_to_constant.get(feed_code, Quote)  # Default to Quote

                    converted_instruments.append((exchange_constant, security_id_str, feed_constant))
                    print(f"Converted instrument: exchange={exchange_code}->{exchange_constant}, security_id={security_id_str}, feed={feed_code}->{feed_constant}")
                else:
                    # Keep as-is if format is different
                    converted_instruments.append(inst)

            print(f"Final converted instruments for DhanFeed: {converted_instruments}")
            print(f"Version: {version}")

            # DhanFeed.__init__ signature: (self, client_id, access_token, instruments, version='v1')
            # Pass client_id and access_token as separate arguments, not as tuple or DhanContext
            return DhanFeed(self.client_id, access_token, converted_instruments, version)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Market Feed not available: {str(e)}")

    def create_order_update(self, access_token: str):
        """Create Order Update instance for real-time order status"""
        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID is not configured")
        try:
            # Try different import paths for OrderSocket
            try:
                from dhanhq.orderupdate import OrderSocket
            except ImportError:
                # Alternative import path
                from dhanhq import orderupdate
                OrderSocket = orderupdate.OrderSocket

            # OrderSocket expects client_id and access_token as separate arguments, not a tuple
            return OrderSocket(self.client_id, access_token)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Order Updates not available: {str(e)}")

    def create_full_depth(self, access_token: str, instruments: List[tuple]):
        """Create Full Depth instance for 20-level market depth"""
        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID is not configured")
        try:
            # Try different import paths for FullDepth
            try:
                from dhanhq import FullDepth
            except ImportError:
                # Alternative import path
                from dhanhq.fulldepth import FullDepth

            return FullDepth((self.client_id, access_token), instruments)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Full Depth not available: {str(e)}")

    def get_instrument_list_csv(self, format_type: str = "compact") -> Dict[str, Any]:
        """
        Fetch instrument list from CSV endpoints

        Args:
            format_type: "compact" or "detailed"

        Returns:
            Dict with success status and parsed CSV data
        """
        try:
            if format_type == "compact":
                url = "https://images.dhan.co/api-data/api-scrip-master.csv"
            elif format_type == "detailed":
                url = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"
            else:
                return {"success": False, "error": "format_type must be 'compact' or 'detailed'"}

            # Fetch CSV data
            response = httpx.get(url, timeout=60.0)
            response.raise_for_status()

            # Parse CSV data
            csv_text = response.text
            csv_reader = csv.DictReader(io.StringIO(csv_text))
            instruments = list(csv_reader)

            return {
                "success": True,
                "data": {
                    "instruments": instruments,
                    "count": len(instruments),
                    "format": format_type
                }
            }
        except httpx.HTTPError as e:
            return {"success": False, "error": f"HTTP error fetching instrument list: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error fetching instrument list: {str(e)}"}

    async def sync_instruments_to_db(self, db, format_type: str = "detailed") -> Dict[str, Any]:
        """
        Sync instruments from CSV to database

        Args:
            db: Database instance
            format_type: "compact" or "detailed"

        Returns:
            Dict with success status and sync results
        """
        try:
            # Fetch CSV data
            csv_result = self.get_instrument_list_csv(format_type)
            if not csv_result.get("success"):
                return csv_result

            instruments = csv_result["data"]["instruments"]

            # Save to database
            result = await db.save_instruments(instruments, format_type)

            return {
                "success": True,
                "data": {
                    "synced_count": result.get("count", 0),
                    "updated_at": result.get("updated_at"),
                    "format": format_type
                }
            }
        except Exception as e:
            return {"success": False, "error": f"Error syncing instruments to database: {str(e)}"}

    async def get_instrument_list_segmentwise(self, exchange_segment: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch detailed instrument list for a particular exchange and segment

        Note: This endpoint does not require authentication, but access_token is kept
        as optional parameter for backward compatibility.

        Args:
            exchange_segment: Exchange segment (e.g., "NSE_EQ", "BSE_EQ", "MCX_COM", "IDX_I")
            access_token: Optional - not required for this endpoint

        Returns:
            Dict with success status and instrument list data
        """
        try:
            # DhanHQ API endpoint format: https://api.dhan.co/v2/instrument/{exchange_segment}
            # For indices, use IDX_I directly
            url = f"https://api.dhan.co/v2/instrument/{exchange_segment}"

            # No authentication headers needed
            headers = {}

            # Fetch instrument list using async client
            # Note: DhanHQ API returns 302 redirect to CSV file, so we need to follow redirects
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=headers, timeout=30.0)

                # Get response text first for debugging
                response_text = ""
                try:
                    response_text = response.text
                except:
                    pass

                # Check response status
                if response.status_code not in [200, 302]:
                    error_msg = response_text or f"HTTP {response.status_code}"
                    try:
                        error_json = response.json()
                        error_msg = error_json.get("message") or error_json.get("error") or error_json.get("detail") or error_msg
                    except:
                        pass

                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {error_msg}",
                        "url": url,
                        "response_text": response_text[:500] if response_text else ""  # Include first 500 chars for debugging
                    }

                # Check if response is CSV (DhanHQ returns CSV for instrument lists via redirect)
                content_type = response.headers.get("content-type", "").lower()
                # Check if it's CSV: content-type contains csv, or starts with CSV headers (EXCH_ID, SECURITY_ID, etc.)
                is_csv = (
                    "csv" in content_type or
                    (response_text and response_text.strip().startswith(("SECURITY_ID", "EXCH_ID", "SYMBOL_NAME"))) or
                    (response_text and len(response_text) > 50 and "," in response_text[:200] and "\n" in response_text[:500])
                )

                if is_csv:
                    # Parse CSV response
                    try:
                        import io
                        csv_reader = csv.DictReader(io.StringIO(response_text))
                        data = list(csv_reader)
                    except Exception as e:
                        return {
                            "success": False,
                            "error": f"Invalid CSV response from API: {str(e)}",
                            "url": url,
                            "response_text": response_text[:500] if response_text else ""
                        }
                else:
                    # Parse JSON response
                    try:
                        data = response.json()
                    except json.JSONDecodeError as e:
                        return {
                            "success": False,
                            "error": f"Invalid JSON response from API: {str(e)}",
                            "url": url,
                            "response_text": response_text[:500] if response_text else ""
                        }

                    # Handle case where API returns error in JSON
                    if isinstance(data, dict):
                        if "status" in data and data.get("status") != "success":
                            error_msg = data.get("message") or data.get("error") or data.get("detail") or "Unknown error from API"
                            return {
                                "success": False,
                                "error": error_msg,
                                "url": url
                            }
                        # Some APIs return data wrapped in a "data" field
                        if "data" in data and isinstance(data["data"], list):
                            data = data["data"]

            return {
                "success": True,
                "data": {
                    "instruments": data if isinstance(data, list) else [data] if data else [],
                    "exchange_segment": exchange_segment,
                    "count": len(data) if isinstance(data, list) else (1 if data else 0)
                }
            }
        except httpx.HTTPStatusError as e:
            error_text = ""
            try:
                if hasattr(e, 'response') and e.response:
                    error_text = e.response.text
                    try:
                        error_json = e.response.json()
                        error_text = error_json.get("message") or error_json.get("error") or error_text
                    except:
                        pass
            except:
                pass
            return {
                "success": False,
                "error": f"HTTP error {e.response.status_code if hasattr(e, 'response') else 'unknown'}: {error_text or str(e)}",
                "url": url if 'url' in locals() else "unknown"
            }
        except httpx.HTTPError as e:
            return {
                "success": False,
                "error": f"HTTP error fetching instrument list: {str(e)}",
                "url": url if 'url' in locals() else "unknown"
            }
        except Exception as e:
            import traceback
            error_detail = str(e) if str(e) else repr(e)
            print(f"Error in get_instrument_list_segmentwise: {error_detail}")
            print(traceback.format_exc())
            return {
                "success": False,
                "error": f"Error fetching instrument list: {error_detail}",
                "url": url if 'url' in locals() else "unknown"
            }

# Global trading service instance
trading_service = TradingService()

