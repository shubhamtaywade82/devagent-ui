"""
Trading module for DhanHQ integration
"""
from dhanhq import dhanhq
from typing import Optional, Dict, List, Any
import os
import httpx
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
        """Get historical data"""
        try:
            dhan = self.get_dhan_instance(access_token)

            if interval == "daily":
                data = dhan.historical_daily_data(
                    security_id, exchange_segment, instrument_type, from_date, to_date
                )
            else:
                data = dhan.intraday_minute_data(
                    security_id, exchange_segment, instrument_type, from_date, to_date
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

# Global trading service instance
trading_service = TradingService()

