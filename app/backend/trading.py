"""
Trading module for DhanHQ integration
"""
from dhanhq import DhanLogin, DhanContext, dhanhq
from typing import Optional, Dict, List, Any
import os
from dotenv import load_dotenv

load_dotenv()

class TradingService:
    """Service for managing DhanHQ trading operations"""

    def __init__(self):
        self.client_id = os.getenv("DHAN_CLIENT_ID")
        self.app_id = os.getenv("DHAN_APP_ID")
        self.app_secret = os.getenv("DHAN_APP_SECRET")
        self.dhan_login = None
        self.dhan_context = None
        self.dhan = None

        if self.client_id:
            self.dhan_login = DhanLogin(self.client_id)

    def authenticate_with_pin(self, pin: str, totp: str) -> Dict[str, Any]:
        """Authenticate using PIN and TOTP"""
        try:
            access_token_data = self.dhan_login.generate_token(pin, totp)
            return {
                "success": True,
                "access_token": access_token_data.get("access_token"),
                "refresh_token": access_token_data.get("refresh_token"),
                "expires_in": access_token_data.get("expires_in")
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def authenticate_oauth(self, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Generate OAuth consent URL"""
        try:
            consent_id = self.dhan_login.generate_login_session(app_id, app_secret)
            return {
                "success": True,
                "consent_id": consent_id,
                "login_url": f"https://api.dhan.co/oauth/authorize?consent_id={consent_id}"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def consume_token_id(self, token_id: str, app_id: str, app_secret: str) -> Dict[str, Any]:
        """Consume token ID from OAuth redirect"""
        try:
            access_token = self.dhan_login.consume_token_id(token_id, app_id, app_secret)
            return {"success": True, "access_token": access_token}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def initialize_context(self, access_token: str):
        """Initialize DhanHQ context with access token"""
        if not self.client_id:
            raise ValueError("DHAN_CLIENT_ID not configured")
        self.dhan_context = DhanContext(self.client_id, access_token)
        self.dhan = dhanhq(self.dhan_context)
        return True

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """Get user profile information"""
        try:
            user_info = self.dhan_login.user_profile(access_token)
            return {"success": True, "data": user_info}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def place_order(self, access_token: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Place a trading order"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)

            result = self.dhan.place_order(
                security_id=order_data["security_id"],
                exchange_segment=order_data["exchange_segment"],
                transaction_type=order_data["transaction_type"],
                quantity=order_data["quantity"],
                order_type=order_data["order_type"],
                product_type=order_data["product_type"],
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
            if not self.dhan:
                self.initialize_context(access_token)
            orders = self.dhan.get_order_list()
            return {"success": True, "data": orders}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_order_by_id(self, access_token: str, order_id: str) -> Dict[str, Any]:
        """Get order by ID"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            order = self.dhan.get_order_by_id(order_id)
            return {"success": True, "data": order}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cancel_order(self, access_token: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            result = self.dhan.cancel_order(order_id)
            return {"success": True, "data": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def modify_order(self, access_token: str, order_id: str, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an order"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            result = self.dhan.modify_order(
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
            if not self.dhan:
                self.initialize_context(access_token)
            positions = self.dhan.get_positions()
            return {"success": True, "data": positions}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_holdings(self, access_token: str) -> Dict[str, Any]:
        """Get current holdings"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            holdings = self.dhan.get_holdings()
            return {"success": True, "data": holdings}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_fund_limits(self, access_token: str) -> Dict[str, Any]:
        """Get fund limits and margin details"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            funds = self.dhan.get_fund_limits()
            return {"success": True, "data": funds}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_market_quote(self, access_token: str, securities: Dict[str, List[int]]) -> Dict[str, Any]:
        """Get market quote data"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            quote = self.dhan.ohlc_data(securities=securities)
            return {"success": True, "data": quote}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_option_chain(self, access_token: str, under_security_id: int,
                        under_exchange_segment: str, expiry: str) -> Dict[str, Any]:
        """Get option chain data"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            chain = self.dhan.option_chain(
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
            if not self.dhan:
                self.initialize_context(access_token)

            if interval == "daily":
                data = self.dhan.historical_daily_data(
                    security_id, exchange_segment, instrument_type, from_date, to_date
                )
            else:
                data = self.dhan.intraday_minute_data(
                    security_id, exchange_segment, instrument_type, from_date, to_date
                )
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_security_list(self, access_token: str, format_type: str = "compact") -> Dict[str, Any]:
        """Get security/instrument list"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            securities = self.dhan.fetch_security_list(format_type)
            return {"success": True, "data": securities}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_expiry_list(self, access_token: str, under_security_id: int,
                       under_exchange_segment: str) -> Dict[str, Any]:
        """Get expiry list for underlying"""
        try:
            if not self.dhan:
                self.initialize_context(access_token)
            expiries = self.dhan.expiry_list(
                under_security_id=under_security_id,
                under_exchange_segment=under_exchange_segment
            )
            return {"success": True, "data": expiries}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Global trading service instance
trading_service = TradingService()

