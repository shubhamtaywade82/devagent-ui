"""
Trading module for DhanHQ integration
"""
from dhanhq import dhanhq
from typing import Optional, Dict, List, Any, Callable
import os
import httpx
import asyncio
import json
import csv
import io
from datetime import datetime, timedelta
from dotenv import load_dotenv

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
            quote = dhan.ohlc_data(securities=securities)
            return {"success": True, "data": quote}
        except Exception as e:
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
                           from_date: str, to_date: str, interval: str = "daily") -> Dict[str, Any]:
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
            security_id_str = str(security_id)

            # Map exchange segment string to dhan constant if possible
            # Official example uses: dhan.NSE, dhan.BSE, etc.
            exchange_constant = None
            if hasattr(dhan, 'NSE') and exchange_segment.upper().startswith('NSE'):
                exchange_constant = dhan.NSE
            elif hasattr(dhan, 'BSE') and exchange_segment.upper().startswith('BSE'):
                exchange_constant = dhan.BSE
            elif hasattr(dhan, 'MCX') and exchange_segment.upper().startswith('MCX'):
                exchange_constant = dhan.MCX
            elif hasattr(dhan, 'NCDEX') and exchange_segment.upper().startswith('NCDEX'):
                exchange_constant = dhan.NCDEX

            # Use constant if available, otherwise use original string
            exchange_seg = exchange_constant if exchange_constant is not None else exchange_segment

            # Fetch data based on interval type
            if interval.lower() in ["daily", "day"]:
                # Daily historical data (per official example)
                data = dhan.historical_daily_data(
                    security_id=security_id_str,
                    exchange_segment=exchange_seg,
                    instrument_type=instrument_type,
                    from_date=from_date,
                    to_date=to_date
                )
            else:
                # Intraday minute data (per official example)
                # Supports: "intraday", "minute", "intraday_minute"
                data = dhan.intraday_minute_data(
                    security_id=security_id_str,
                    exchange_segment=exchange_seg,
                    instrument_type=instrument_type,
                    from_date=from_date,
                    to_date=to_date
                )

            return {"success": True, "data": data}
        except Exception as e:
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
            # Import DhanFeed (actual class name in dhanhq library)
            from dhanhq.marketfeed import DhanFeed

            # Convert security IDs to strings (per official example pattern)
            # The example shows: (DhanFeed.NSE, "1333", DhanFeed.Ticker)
            converted_instruments = []
            for inst in instruments:
                if len(inst) >= 3:
                    exchange_code, security_id, feed_code = inst[0], inst[1], inst[2]
                    # Convert security_id to string to match official example
                    security_id_str = str(security_id) if not isinstance(security_id, str) else security_id
                    converted_instruments.append((exchange_code, security_id_str, feed_code))
                else:
                    # Keep as-is if format is different
                    converted_instruments.append(inst)

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

    def get_instrument_list_segmentwise(self, exchange_segment: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch detailed instrument list for a particular exchange and segment

        Note: This endpoint does not require authentication, but access_token is kept
        as optional parameter for backward compatibility.

        Args:
            exchange_segment: Exchange segment (e.g., "NSE_EQ", "BSE_EQ", "MCX_COM")
            access_token: Optional - not required for this endpoint

        Returns:
            Dict with success status and instrument list data
        """
        try:
            url = f"https://api.dhan.co/v2/instrument/{exchange_segment}"

            # No authentication headers needed
            headers = {}

            # Fetch instrument list
            response = httpx.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()

            data = response.json()

            return {
                "success": True,
                "data": {
                    "instruments": data,
                    "exchange_segment": exchange_segment,
                    "count": len(data) if isinstance(data, list) else 0
                }
            }
        except httpx.HTTPStatusError as e:
            return {"success": False, "error": f"HTTP error: {e.response.status_code} - {e.response.text}"}
        except httpx.HTTPError as e:
            return {"success": False, "error": f"HTTP error fetching instrument list: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Error fetching instrument list: {str(e)}"}

# Global trading service instance
trading_service = TradingService()

