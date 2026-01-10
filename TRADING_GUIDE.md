# Trading Agent Guide

DevAgent has been transformed into a comprehensive trading platform using DhanHQ Python SDK. This guide covers all trading features and how to use them.

## Features

### 🎯 Trading Capabilities
- **Order Management**: Place, modify, cancel orders for Equity, F&O
- **Portfolio Management**: View holdings, positions, and P&L
- **Market Data**: Real-time quotes, option chains, historical data
- **Fund Management**: Check available balance, margin used, fund limits
- **AI Trading Assistant**: Get trading strategies and analysis from AI

### 🔐 Authentication

Two authentication methods are supported:

#### Method 1: PIN & TOTP
```javascript
// Frontend automatically handles this
POST /api/trading/auth/pin
{
  "pin": "YOUR_PIN",
  "totp": "TOTP_FROM_AUTHENTICATOR"
}
```

#### Method 2: OAuth Flow
```javascript
// Step 1: Initialize OAuth
POST /api/trading/auth/oauth
// Returns login_url - open in browser

// Step 2: After login, get token_id from redirect URL
POST /api/trading/auth/consume
{
  "token_id": "TOKEN_ID_FROM_REDIRECT"
}
```

## Configuration

### Backend Environment Variables

Add to `/app/backend/.env`:

```env
# DhanHQ Configuration
DHAN_CLIENT_ID=your_client_id
DHAN_APP_ID=your_app_id  # For OAuth
DHAN_APP_SECRET=your_app_secret  # For OAuth
```

### Getting DhanHQ Credentials

1. Register at [Dhan Developer Portal](https://dhan.co)
2. Create an application
3. Get your Client ID, App ID, and App Secret
4. Add them to `.env` file

## API Endpoints

### Authentication
- `POST /api/trading/auth/pin` - Authenticate with PIN & TOTP
- `POST /api/trading/auth/oauth` - Initialize OAuth flow
- `POST /api/trading/auth/consume` - Consume OAuth token
- `POST /api/trading/profile` - Get user profile

### Orders
- `POST /api/trading/orders/place` - Place new order
- `POST /api/trading/orders` - Get all orders
- `GET /api/trading/orders/{order_id}` - Get order by ID
- `POST /api/trading/orders/{order_id}/cancel` - Cancel order
- `POST /api/trading/orders/{order_id}/modify` - Modify order

### Portfolio
- `POST /api/trading/positions` - Get open positions
- `POST /api/trading/holdings` - Get holdings
- `POST /api/trading/funds` - Get fund limits and margin

### Market Data
- `POST /api/trading/market/quote` - Get market quote
- `POST /api/trading/market/option-chain` - Get option chain
- `POST /api/trading/market/historical` - Get historical data
- `POST /api/trading/securities` - Get security list
- `POST /api/trading/expiry-list` - Get expiry list

## Usage Examples

### Place Order

```javascript
const order = {
  access_token: "your_access_token",
  security_id: "1333",  // HDFC Bank
  exchange_segment: "NSE",
  transaction_type: "BUY",
  quantity: 10,
  order_type: "MARKET",
  product_type: "INTRA",
  price: 0  // 0 for MARKET orders
}

const response = await api.placeOrder(order)
```

### Get Positions

```javascript
const positions = await api.getPositions(accessToken)
// Returns array of open positions with P&L
```

### Get Market Quote

```javascript
const quote = await api.getMarketQuote({
  access_token: accessToken,
  securities: { "NSE_EQ": [1333] }  // HDFC Bank
})
```

## Trading Dashboard

The trading dashboard provides:

1. **Dashboard Tab**
   - Available balance
   - Total P&L
   - Margin used
   - Active orders count
   - Open positions table
   - Recent orders

2. **Place Order Tab**
   - Order placement form
   - Support for MARKET, LIMIT, SL, SL-M orders
   - Equity and F&O support

3. **Portfolio Tab**
   - Holdings view
   - Positions view
   - Fund summary

4. **Market Data Tab**
   - Market quote search
   - Option chain (coming soon)
   - Historical data (coming soon)

## AI Trading Assistant

The AI chat sidebar can now help with:
- Trading strategies
- Market analysis
- Risk management suggestions
- Trade recommendations (when using options analysis model)

## Integration with Options Analysis

When using the Ollama Router with `nemesis-options-analyst` model:
- Pass `task: "options"` in chat requests
- Get structured SMC/AVRZ analysis
- Receive BUY_CE_ALLOWED, BUY_PE_ALLOWED, or NO_TRADE signals

## Security Notes

- Access tokens are stored in browser localStorage
- Never commit `.env` files with credentials
- Use environment variables for all sensitive data
- Tokens expire - implement token renewal

## Next Steps

1. Configure DhanHQ credentials in `.env`
2. Restart backend: `docker-compose restart backend`
3. Navigate to Trading Dashboard from landing page
4. Authenticate with your Dhan account
5. Start trading!

## References

- [DhanHQ Python SDK](https://github.com/dhan-oss/DhanHQ-py)
- [Dhan API Documentation](https://dhan.co)
- [Dhan Developer Portal](https://dhan.co)

