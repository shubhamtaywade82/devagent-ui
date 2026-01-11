# Ollama + DhanHQ Tools - Quick Reference

## Overview

This guide shows how DhanHQ APIs are integrated as tools for Ollama/LLM agents, based on the current implementation in this codebase.

## Files Created

1. **`app/backend/tools.py`** - Tool definitions (OpenAI function calling format)
2. **`app/backend/tool_executor.py`** - Tool execution handler
3. **`OLLAMA_DHANHQ_TOOLS_INTEGRATION.md`** - Detailed integration guide

## Current Implementation Structure

### DhanHQ APIs (trading.py)

All DhanHQ operations are wrapped in `TradingService` class:

```python
# app/backend/trading.py
class TradingService:
    def get_market_quote(access_token, securities)
    def get_historical_data(access_token, security_id, ...)
    def get_positions(access_token)
    def get_holdings(access_token)
    def get_fund_limits(access_token)
    def get_option_chain(access_token, ...)
    def place_order(access_token, order_data)
    # ... and more
```

### Ollama Integration (main.py)

Current chat endpoints:
- `/api/chat` - Non-streaming
- `/api/chat/stream` - Streaming
- Supports: Native Ollama, OpenAI-compatible APIs, Ollama Router

## How Tools Work

### 1. Tool Definition (tools.py)

Tools are defined in OpenAI function calling format:

```python
{
    "type": "function",
    "function": {
        "name": "get_market_quote",
        "description": "Get real-time market quote...",
        "parameters": {
            "type": "object",
            "properties": {
                "securities": {...}
            }
        }
    }
}
```

### 2. Tool Execution (tool_executor.py)

When LLM calls a function, `execute_tool()` routes to TradingService:

```python
async def execute_tool(function_name, function_args, access_token):
    if function_name == "get_market_quote":
        return trading_service.get_market_quote(access_token, ...)
    # ... route other functions
```

### 3. Integration Flow

```
User Query → Ollama/LLM → Function Call → execute_tool() → TradingService → DhanHQ API → Response
```

## Available Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `get_market_quote` | Real-time OHLC data | `securities: dict` |
| `get_historical_data` | Historical price data | `security_id, exchange_segment, from_date, to_date, interval` |
| `get_positions` | Open positions with P&L | None |
| `get_holdings` | Portfolio holdings | None |
| `get_fund_limits` | Available balance & margin | None |
| `get_option_chain` | Options chain data | `under_security_id, under_exchange_segment, expiry` |
| `get_orders` | Order list | None |
| `get_trades` | Executed trades | None |
| `analyze_market` | Composite analysis | `security_id, exchange_segment, days` |

## Example Usage

### User Query
"What's the current price of HDFC Bank and show me the trend for last 30 days?"

### Agent Flow
1. Agent calls `get_market_quote({"NSE_EQ": [1333]})`
2. Agent calls `get_historical_data(1333, "NSE_EQ", "EQUITY", "2024-01-01", "2024-01-31", "daily")`
3. Agent analyzes data and responds

### Response Format
```json
{
    "success": true,
    "data": {
        "current_price": 1650.50,
        "historical": [...],
        "trend": {
            "change": 50.25,
            "change_percent": 3.15,
            "direction": "up"
        }
    }
}
```

## Integration Steps

### Step 1: Add Tools to Chat Endpoint

Modify `main.py` chat endpoint to include tools:

```python
from tools import DHANHQ_TOOLS
from tool_executor import execute_tool

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    # ... existing code ...

    if USE_OPENAI_API and OPENAI_API_BASE:
        # Add tools to payload
        payload = {
            "model": OPENAI_API_MODEL,
            "messages": messages,
            "tools": DHANHQ_TOOLS,  # Add this
            "tool_choice": "auto"
        }
        # Handle tool calls in response
```

### Step 2: Handle Function Calls

```python
# In chat endpoint
response = await client.post(url, json=payload)
data = response.json()
message = data["choices"][0]["message"]

if "tool_calls" in message:
    # Execute each tool call
    for tool_call in message["tool_calls"]:
        function_name = tool_call["function"]["name"]
        function_args = json.loads(tool_call["function"]["arguments"])
        result = await execute_tool(function_name, function_args, access_token)
        # Send result back to LLM
```

### Step 3: Update Request Model

Add `access_token` to `ChatRequest`:

```python
class ChatRequest(BaseModel):
    message: str
    context: Optional[List[str]] = None
    task: Optional[str] = None
    access_token: Optional[str] = None  # Add this
```

## Key Points

1. **Access Token Required**: All trading operations need `access_token`
2. **Error Handling**: All TradingService methods return `{"success": bool, ...}`
3. **Tool Format**: Follows OpenAI function calling spec (compatible with many LLMs)
4. **Composite Functions**: `analyze_market` combines multiple API calls

## Testing

### Test with OpenAI-Compatible API

```bash
# Set in .env
USE_OPENAI_API=true
OPENAI_API_BASE=http://localhost:8080/v1
OPENAI_API_MODEL=nemesis-coder
```

### Test Tool Execution

```python
# Direct test
from tool_executor import execute_tool

result = await execute_tool(
    "get_market_quote",
    {"securities": {"NSE_EQ": [1333]}},
    access_token="your_token"
)
print(result)
```

## References

- **DhanHQ APIs**: `app/backend/trading.py`
- **Ollama Integration**: `app/backend/main.py` (lines 472-603)
- **Tool Definitions**: `app/backend/tools.py`
- **Tool Executor**: `app/backend/tool_executor.py`
- **Detailed Guide**: `OLLAMA_DHANHQ_TOOLS_INTEGRATION.md`

## Next Steps

1. ✅ Tool definitions created (`tools.py`)
2. ✅ Tool executor created (`tool_executor.py`)
3. ⏳ Integrate with chat endpoint (`main.py`)
4. ⏳ Add access_token to ChatRequest
5. ⏳ Test with OpenAI-compatible API
6. ⏳ Add support for native Ollama function calling (if supported)

