# Ollama + DhanHQ Tools Integration Guide

This document explains how to integrate DhanHQ APIs as tools/functions for Ollama agents, enabling AI-powered trading analysis and operations.

## Overview

The integration pattern follows OpenAI's function calling format, which is compatible with:
- Ollama (with function calling support)
- OpenAI-compatible APIs (Open WebUI, vLLM, Ollama Router, etc.)
- Any LLM that supports function calling

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Ollama/LLM Agent                         │
│  (Receives tool definitions, makes function calls)          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ Function Call Request
                       │ (JSON with function name + parameters)
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              FastAPI Backend (main.py)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Function Call Handler                                │  │
│  │  - Parses function call from Ollama                   │  │
│  │  - Routes to appropriate TradingService method        │  │
│  │  - Returns results to Ollama                          │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ API Calls
                       ▼
┌─────────────────────────────────────────────────────────────┐
│           TradingService (trading.py)                       │
│  - get_market_quote()                                        │
│  - get_historical_data()                                    │
│  - get_positions()                                          │
│  - get_holdings()                                           │
│  - place_order()                                             │
│  - get_option_chain()                                        │
│  - ... (all DhanHQ API methods)                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       │ DhanHQ SDK
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              DhanHQ Python SDK                               │
│  (dhanhq library - v2.2.0)                                  │
└─────────────────────────────────────────────────────────────┘
```

## Current Implementation Analysis

### 1. DhanHQ APIs Available (from `trading.py`)

All these methods can be exposed as tools to Ollama:

#### Market Data Tools
- `get_market_quote()` - Get real-time OHLC data
- `get_historical_data()` - Get daily/intraday historical data
- `get_option_chain()` - Get options chain for underlying
- `get_security_list()` - Search for securities/instruments
- `get_expiry_list()` - Get expiry dates for F&O

#### Portfolio Tools
- `get_positions()` - Get open positions with P&L
- `get_holdings()` - Get holdings
- `get_fund_limits()` - Get available balance, margin

#### Order Management Tools
- `place_order()` - Place new order
- `get_orders()` - Get all orders
- `get_order_by_id()` - Get specific order
- `cancel_order()` - Cancel order
- `modify_order()` - Modify existing order
- `get_trades()` - Get executed trades

#### Analysis Tools
- `calculate_margin()` - Calculate margin for order
- `get_ledger()` - Get ledger report

### 2. Current Ollama Integration (from `main.py`)

**Current State:**
- Basic chat integration using `/api/generate` or `/api/chat`
- No function calling tools exposed
- Simple prompt-based interaction

**Example:**
```python
# Current implementation (main.py:472-508)
async def generate_ollama_response_stream(prompt: str):
    url = f"{OLLAMA_BASE_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True
    }
    # No tools/functions defined
```

## Implementation: Adding Function Calling

### Step 1: Define Tool Schemas

Create a module `app/backend/tools.py` with tool definitions:

```python
"""
Tool definitions for Ollama/LLM function calling
Following OpenAI function calling format
"""

DHANHQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_market_quote",
            "description": "Get real-time market quote (OHLC data) for securities. Use this to check current prices, open, high, low, close, and volume.",
            "parameters": {
                "type": "object",
                "properties": {
                    "securities": {
                        "type": "object",
                        "description": "Dictionary mapping exchange segments to list of security IDs. Example: {'NSE_EQ': [1333, 11536]}",
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
            "description": "Get historical price data (daily or intraday minute data) for analysis. Use for technical analysis, backtesting, or trend analysis.",
            "parameters": {
                "type": "object",
                "properties": {
                    "security_id": {
                        "type": "integer",
                        "description": "Security ID (e.g., 1333 for HDFC Bank)"
                    },
                    "exchange_segment": {
                        "type": "string",
                        "description": "Exchange segment (e.g., 'NSE_EQ', 'BSE_EQ')",
                        "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO", "MCX_COM", "NCDEX_COM"]
                    },
                    "instrument_type": {
                        "type": "string",
                        "description": "Instrument type",
                        "enum": ["EQUITY", "FUTURES", "OPTIONS"]
                    },
                    "from_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format"
                    },
                    "to_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format"
                    },
                    "interval": {
                        "type": "string",
                        "description": "Data interval",
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
            "description": "Get current open positions with P&L. Use to check active trades, unrealized P&L, and position details.",
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
            "description": "Get current holdings (stocks owned). Use to check portfolio holdings.",
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
            "description": "Get available balance, margin used, and fund limits. Use to check if user has sufficient funds for trading.",
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
            "description": "Get options chain for an underlying security. Use for options analysis, finding strike prices, and analyzing option premiums.",
            "parameters": {
                "type": "object",
                "properties": {
                    "under_security_id": {
                        "type": "integer",
                        "description": "Underlying security ID (e.g., 1333 for NIFTY)"
                    },
                    "under_exchange_segment": {
                        "type": "string",
                        "description": "Underlying exchange segment",
                        "enum": ["NSE_EQ", "NSE_FO", "BSE_EQ", "BSE_FO"]
                    },
                    "expiry": {
                        "type": "string",
                        "description": "Expiry date in YYYY-MM-DD format"
                    }
                },
                "required": ["under_security_id", "under_exchange_segment", "expiry"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_securities",
            "description": "Search for securities/instruments by symbol or name. Use to find security IDs for trading.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (symbol or name, e.g., 'HDFC', 'RELIANCE', 'NIFTY')"
                    },
                    "exchange_segment": {
                        "type": "string",
                        "description": "Optional: Filter by exchange segment",
                        "enum": ["NSE_EQ", "BSE_EQ", "NSE_FO", "BSE_FO"]
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
            "description": "Analyze market conditions by fetching current quotes and historical data. Provides comprehensive market analysis.",
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
                        "description": "Number of days of historical data to analyze",
                        "default": 30
                    }
                },
                "required": ["security_id", "exchange_segment"]
            }
        }
    }
]
```

### Step 2: Update Ollama Integration with Tools

Modify `main.py` to support function calling:

```python
# Add to main.py

from tools import DHANHQ_TOOLS

async def generate_ollama_with_tools(prompt: str, access_token: str = None):
    """
    Generate response from Ollama with function calling support

    For OpenAI-compatible APIs, use tools parameter.
    For native Ollama, we need to use a different approach.
    """
    if USE_OPENAI_API and OPENAI_API_BASE:
        # OpenAI-compatible API with function calling
        return await generate_openai_with_tools(prompt, access_token)
    else:
        # Native Ollama - use structured prompts with tool descriptions
        return await generate_ollama_with_structured_prompts(prompt, access_token)

async def generate_openai_with_tools(prompt: str, access_token: str = None):
    """Generate response with function calling for OpenAI-compatible APIs"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        url = f"{OPENAI_API_BASE}/chat/completions"

        messages = [
            {
                "role": "system",
                "content": """You are a trading assistant with access to DhanHQ APIs.
                You can analyze markets, check positions, get quotes, and provide trading insights.
                Use the available tools to fetch real-time data and provide accurate analysis."""
            },
            {"role": "user", "content": prompt}
        ]

        payload = {
            "model": OPENAI_API_MODEL,
            "messages": messages,
            "tools": DHANHQ_TOOLS,
            "tool_choice": "auto",  # Let model decide when to use tools
            "stream": False
        }

        response = await client.post(url, json=payload)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        data = response.json()
        message = data["choices"][0]["message"]

        # Check if model wants to call a function
        if "tool_calls" in message:
            # Execute function calls
            tool_results = []
            for tool_call in message["tool_calls"]:
                function_name = tool_call["function"]["name"]
                function_args = json.loads(tool_call["function"]["arguments"])

                # Execute the function
                result = await execute_tool(function_name, function_args, access_token)
                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": json.dumps(result)
                })

            # Send tool results back to model
            messages.append(message)  # Add assistant message with tool calls
            messages.extend(tool_results)  # Add tool results

            # Get final response
            payload["messages"] = messages
            response = await client.post(url, json=payload)
            data = response.json()
            return {"response": data["choices"][0]["message"]["content"]}
        else:
            return {"response": message["content"]}

async def execute_tool(function_name: str, function_args: dict, access_token: str):
    """Execute a tool/function call"""
    if not access_token:
        return {"error": "Access token required for trading operations"}

    try:
        if function_name == "get_market_quote":
            return trading_service.get_market_quote(
                access_token,
                function_args["securities"]
            )

        elif function_name == "get_historical_data":
            return trading_service.get_historical_data(
                access_token,
                function_args["security_id"],
                function_args["exchange_segment"],
                function_args["instrument_type"],
                function_args["from_date"],
                function_args["to_date"],
                function_args.get("interval", "daily")
            )

        elif function_name == "get_positions":
            return trading_service.get_positions(access_token)

        elif function_name == "get_holdings":
            return trading_service.get_holdings(access_token)

        elif function_name == "get_fund_limits":
            return trading_service.get_fund_limits(access_token)

        elif function_name == "get_option_chain":
            return trading_service.get_option_chain(
                access_token,
                function_args["under_security_id"],
                function_args["under_exchange_segment"],
                function_args["expiry"]
            )

        elif function_name == "search_securities":
            # This would need to be implemented in TradingService
            # or use the database to search instruments
            return {"error": "Search securities not yet implemented"}

        elif function_name == "analyze_market":
            # Composite function that combines multiple API calls
            security_id = function_args["security_id"]
            exchange_segment = function_args["exchange_segment"]
            days = function_args.get("days", 30)

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
                "EQUITY",
                from_date,
                to_date,
                "daily"
            )

            return {
                "quote": quote_result,
                "historical": historical_result,
                "analysis_period": f"{from_date} to {to_date}"
            }

        else:
            return {"error": f"Unknown function: {function_name}"}

    except Exception as e:
        return {"error": str(e)}
```

### Step 3: Update Chat Endpoint

Modify the chat endpoint to support tools:

```python
@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """Streaming chat endpoint with tool support"""
    try:
        # Extract access_token from request if available
        access_token = getattr(request, 'access_token', None)

        # Build enhanced prompt
        context_parts = []
        if request.context:
            context_parts.append("Context from project files:")
            context_parts.extend(request.context[:3])

        prompt = f"""You are an AI trading assistant with access to real-time market data and trading APIs.

{f"Context: {' '.join(context_parts)}" if context_parts else ""}

User question: {request.message}

You can use available tools to:
- Get real-time market quotes
- Analyze historical data
- Check positions and holdings
- Get option chains
- Analyze market conditions

Provide helpful, accurate trading insights based on real data."""

        if USE_OPENAI_API and OPENAI_API_BASE:
            # Use function calling
            return StreamingResponse(
                generate_openai_with_tools_stream(prompt, access_token),
                media_type="text/event-stream"
            )
        else:
            # Fallback to basic Ollama
            return StreamingResponse(
                generate_ollama_response_stream(prompt),
                media_type="text/event-stream"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Step 4: Add Request Model for Access Token

```python
# In models.py or main.py

class ChatRequest(BaseModel):
    message: str
    context: Optional[List[str]] = None
    task: Optional[str] = None
    access_token: Optional[str] = None  # Add this for trading operations
```

## Usage Examples

### Example 1: Market Analysis

**User:** "What's the current price of HDFC Bank and show me the last 30 days trend?"

**Agent Flow:**
1. Agent calls `search_securities("HDFC")` → Gets security_id: 1333
2. Agent calls `get_market_quote()` → Gets current price
3. Agent calls `get_historical_data()` → Gets 30 days data
4. Agent analyzes and responds with price + trend analysis

### Example 2: Portfolio Check

**User:** "What are my current positions and P&L?"

**Agent Flow:**
1. Agent calls `get_positions()` → Gets positions with P&L
2. Agent analyzes and summarizes positions

### Example 3: Options Analysis

**User:** "Show me NIFTY option chain for next expiry"

**Agent Flow:**
1. Agent calls `search_securities("NIFTY")` → Gets security_id
2. Agent calls `get_expiry_list()` → Gets next expiry
3. Agent calls `get_option_chain()` → Gets option chain
4. Agent analyzes and presents option chain data

## Integration with Ollama Router

If using Ollama Router with specialized models:

```python
# In main.py

if USE_OLLAMA_ROUTER and OLLAMA_ROUTER_BASE:
    headers = {
        "X-Task": "trading"  # Route to trading-specialized model
    }
    # Rest of the function calling logic
```

## Key Points from Current Implementation

1. **DhanHQ SDK Integration** (`trading.py`):
   - Uses `dhanhq` library v2.2.0
   - All methods return `{"success": bool, "data": ...}` or `{"success": bool, "error": ...}`
   - Access token required for all operations

2. **API Endpoints** (`main.py`):
   - All trading endpoints follow pattern: `/api/trading/*`
   - Request models use Pydantic for validation
   - Error handling with proper HTTP status codes

3. **Ollama Integration** (`main.py`):
   - Supports native Ollama (`/api/generate`)
   - Supports OpenAI-compatible APIs (`/v1/chat/completions`)
   - Supports Ollama Router (`/api/chat` with X-Task header)

## Next Steps

1. Create `app/backend/tools.py` with tool definitions
2. Implement `execute_tool()` function to route tool calls to TradingService
3. Update chat endpoints to support function calling
4. Test with OpenAI-compatible API first (easier to debug)
5. Add tool calling support for native Ollama (if model supports it)

## References

- [OpenAI Function Calling](https://platform.openai.com/docs/guides/function-calling)
- [Ollama Function Calling](https://github.com/ollama/ollama/blob/main/docs/function-calling.md)
- Current DhanHQ implementation: `app/backend/trading.py`
- Current Ollama integration: `app/backend/main.py` (lines 472-603)

