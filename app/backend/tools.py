"""
Tool definitions for Ollama/LLM function calling with DhanHQ APIs

This module defines the tools/functions that can be called by Ollama or other LLMs
to interact with DhanHQ trading APIs. Follows OpenAI function calling format.
"""

DHANHQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_quote",
            "description": "Get real-time market quote (OHLC data) for securities. Returns current price, open, high, low, close, volume, and other market data. Use this to check current prices and market status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "securities": {
                        "type": "object",
                        "description": "Dictionary mapping exchange segments to list of security IDs. Example: {'NSE_EQ': [1333, 11536]} for HDFC Bank and Reliance",
                        "additionalProperties": {
                            "type": "array",
                            "items": {"type": "integer"}
                        }
                    }
                },
                "required": ["securities"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_historical_data",
            "description": "Get historical price data (daily or intraday minute data) for technical analysis, backtesting, or trend analysis. Returns OHLCV data for the specified date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "security_id": {
                        "type": "integer",
                        "description": "Security ID (e.g., 1333 for HDFC Bank, 11536 for Reliance)"
                    },
                    "exchange_segment": {
                        "type": "string",
                        "description": "Exchange segment where the security is traded",
                        "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "MCX_COM", "NCDEX_COM"]
                    },
                    "instrument_type": {
                        "type": "string",
                        "description": "Type of instrument",
                        "enum": ["EQUITY", "FUTURES", "OPTIONS"]
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format (e.g., '2024-01-01')"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format (e.g., '2024-01-31')"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval - 'daily' for daily candles, 'intraday' or 'minute' for minute-by-minute data",
                        "enum": ["daily", "intraday", "minute"],
                        "default": "daily"
                    }
                },
                "required": ["security_id", "exchange_segment", "instrument_type", "from_date", "to_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_positions",
            "description": "Get current open positions with P&L. Returns all active trades, unrealized profit/loss, quantity, average price, and current market value. Use to check active trades and their performance.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_holdings",
            "description": "Get current holdings (stocks/securities owned in demat account). Returns list of all holdings with quantity, average price, and current value. Use to check portfolio holdings.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fund_limits",
            "description": "Get available balance, margin used, and fund limits. Returns available cash, margin used, total margin, and other fund details. Use to check if user has sufficient funds for trading.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_option_chain",
            "description": "Get options chain for an underlying security. Returns all available strike prices, call and put option prices (premiums), open interest, and volume. Use for options analysis, finding strike prices, and analyzing option premiums.",
            "parameters": {
                "type": "object",
                "properties": {
                    "under_security_id": {
                        "type": "integer",
                        "description": "Underlying security ID (e.g., 99926000 for NIFTY, 1333 for HDFC Bank)"
                    },
                    "under_exchange_segment": {
                        "type": "string",
                        "description": "Underlying exchange segment",
                        "enum": ["NSE_EQ", "NSE_FO", "BSE_EQ", "BSE_FO"]
                    },
                    "expiry": {
                        "type": "string",
                        "description": "Expiry date in YYYY-MM-DD format (e.g., '2024-01-25')"
                    }
                },
                "required": ["under_security_id", "under_exchange_segment", "expiry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "Get all orders (pending, executed, cancelled). Returns order list with status, quantity, price, order type, and execution details. Use to check order status and history.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_trades",
            "description": "Get all executed trades for today. Returns trade details including execution price, quantity, time, and order ID. Use to check today's trading activity.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_instruments",
            "description": "Search for instruments/securities by symbol name, trading symbol, or underlying symbol. Returns security ID, exchange segment, and instrument details. ALWAYS use this first when user asks about a stock, index, or instrument by name (e.g., 'NIFTY', 'HDFC Bank', 'RELIANCE'). Then use the returned security_id and exchange_segment for other operations like get_market_quote, get_historical_data, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query - symbol name, trading symbol, or underlying symbol (e.g., 'NIFTY', 'HDFC', 'RELIANCE', 'NIFTY 50')"
                    },
                    "exchange_segment": {
                        "type": "string",
                        "description": "Optional: Filter by exchange segment (e.g., 'NSE_EQ', 'NSE_FO', 'BSE_EQ', 'IDX_I' for indices). Leave empty to search all segments.",
                        "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "IDX_I", "MCX_COM", "NCDEX_COM"]
                    },
                    "instrument_type": {
                        "type": "string",
                        "description": "Optional: Filter by instrument type (e.g., 'EQUITY', 'INDEX', 'FUTURES', 'OPTIONS')",
                        "enum": ["EQUITY", "INDEX", "FUTURES", "OPTIONS", "COMMODITY"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return (default: 10)",
                        "default": 20
                    },
                    "exact_match": {
                        "type": "boolean",
                        "description": "Whether to perform exact symbol matching (default: false). If true, symbol must match exactly.",
                        "default": False
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Whether the search should be case sensitive (default: false)",
                        "default": False
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_market",
            "description": "Comprehensive market analysis combining current quotes and historical data. Fetches current price, recent trend, and provides analysis summary. Use for quick market overview and trend analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "security_id": {
                        "type": "integer",
                        "description": "Security ID to analyze"
                    },
                    "exchange_segment": {
                        "type": "string",
                        "description": "Exchange segment",
                        "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO"]
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days of historical data to analyze (default: 30)",
                        "default": 30
                    }
                },
                "required": ["security_id", "exchange_segment"]
            }
        }
    }
]

# Tool execution mapping
TOOL_EXECUTORS = {
    "search_instruments": "search_instruments",
    "get_market_quote": "get_market_quote",
    "get_historical_data": "get_historical_data",
    "get_positions": "get_positions",
    "get_holdings": "get_holdings",
    "get_fund_limits": "get_fund_limits",
    "get_option_chain": "get_option_chain",
    "get_orders": "get_orders",
    "get_trades": "get_trades",
    "analyze_market": "analyze_market"  # Composite function
}

