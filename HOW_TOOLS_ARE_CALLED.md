# How Tools Are Called in the AI Agent

This document explains the complete flow of how tools are invoked in the AI agent system.

## Overview

The AI agent uses **function calling** (also called tool calling) to interact with external APIs. When a user asks a question, the LLM can decide to call one or more tools to fetch real-time data before answering.

## Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER QUERY                                                    │
│    "What's the current price of NIFTY?"                         │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. FRONTEND → BACKEND                                            │
│    POST /api/chat/stream                                         │
│    {                                                             │
│      "message": "What's the current price of NIFTY?",           │
│      "access_token": "eyJ...",                                  │
│      "task": "trading"                                           │
│    }                                                             │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. BACKEND: chat_stream()                                        │
│    - Detects trading request (has access_token)                 │
│    - Loads DHANHQ_TOOLS (tool definitions)                      │
│    - Builds system prompt with tool instructions               │
│    - Calls generate_openai_response() with tools                │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. LLM API CALL (OpenAI-compatible)                              │
│    POST {OPENAI_API_BASE}/chat/completions                      │
│    {                                                             │
│      "model": "nemesis-coder",                                  │
│      "messages": [                                               │
│        {"role": "system", "content": "..."},                    │
│        {"role": "user", "content": "What's the price..."}      │
│      ],                                                          │
│      "tools": [                                                  │
│        {                                                         │
│          "type": "function",                                    │
│          "function": {                                           │
│            "name": "search_instruments",                       │
│            "description": "Search for instruments...",          │
│            "parameters": {...}                                   │
│          }                                                       │
│        },                                                        │
│        {                                                         │
│          "type": "function",                                    │
│          "function": {                                           │
│            "name": "get_market_quote",                          │
│            "description": "Get current prices...",               │
│            "parameters": {...}                                   │
│          }                                                       │
│        }                                                         │
│      ],                                                          │
│      "tool_choice": "auto"  // or "required" for trading        │
│    }                                                             │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. LLM RESPONSE (with tool_calls)                               │
│    {                                                             │
│      "choices": [{                                               │
│        "message": {                                              │
│          "role": "assistant",                                   │
│          "content": null,                                       │
│          "tool_calls": [                                         │
│            {                                                     │
│              "id": "call_abc123",                               │
│              "type": "function",                                 │
│              "function": {                                       │
│                "name": "search_instruments",                    │
│                "arguments": "{\"query\":\"NIFTY\",\"instrument_type\":\"INDEX\"}" │
│              }                                                   │
│            }                                                     │
│          ]                                                       │
│        }                                                         │
│      }]                                                          │
│    }                                                             │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. BACKEND: Parse tool_calls                                     │
│    for tool_call in message["tool_calls"]:                      │
│      function_name = tool_call["function"]["name"]             │
│      function_args = json.loads(tool_call["function"]["arguments"]) │
│                                                                  │
│      Example:                                                    │
│        function_name = "search_instruments"                     │
│        function_args = {                                         │
│          "query": "NIFTY",                                      │
│          "instrument_type": "INDEX"                              │
│        }                                                         │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. BACKEND: Execute Tool                                         │
│    result = await execute_tool(                                 │
│      function_name="search_instruments",                        │
│      function_args={"query": "NIFTY", ...},                     │
│      access_token="eyJ..."                                      │
│    )                                                             │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. tool_executor.py: execute_tool()                              │
│    - Tries new tool router (agent.tool_router)                  │
│    - Falls back to legacy execution if needed                    │
│    - Routes to appropriate handler:                              │
│      * search_instruments → search_instruments()                │
│      * get_market_quote → trading_service.get_market_quote()    │
│      * get_historical_data → trading_service.get_historical_data() │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Tool Execution                                                │
│    - Calls DhanHQ API via trading_service                      │
│    - Returns result:                                            │
│      {                                                           │
│        "success": true,                                         │
│        "data": {                                                │
│          "instruments": [                                       │
│            {                                                     │
│              "security_id": 13,                                 │
│              "exchange_segment": "IDX_I",                       │
│              "symbol_name": "NIFTY",                            │
│              ...                                                 │
│            }                                                     │
│          ]                                                       │
│        }                                                         │
│      }                                                           │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. BACKEND: Format Tool Result                                  │
│     - Formats result for LLM understanding                      │
│     - Adds to tool_results array:                               │
│       {                                                          │
│         "role": "tool",                                         │
│         "tool_call_id": "call_abc123",                          │
│         "name": "search_instruments",                           │
│         "content": "✅ Success!\n\nFound NIFTY 50..."           │
│       }                                                          │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. AGENTIC LOOP: Send Results Back to LLM                      │
│     messages.append(assistant_message_with_tool_calls)            │
│     messages.extend(tool_results)                                │
│                                                                  │
│     POST {OPENAI_API_BASE}/chat/completions                     │
│     {                                                            │
│       "messages": [                                              │
│         {"role": "user", "content": "What's the price..."},    │
│         {                                                        │
│           "role": "assistant",                                  │
│           "tool_calls": [...]                                   │
│         },                                                       │
│         {                                                        │
│           "role": "tool",                                       │
│           "tool_call_id": "call_abc123",                        │
│           "content": "Found NIFTY 50: security_id=13..."       │
│         }                                                       │
│       ],                                                         │
│       "tools": [...]  // Still available for next round         │
│     }                                                            │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. LLM: Makes Second Tool Call                                  │
│     Now that LLM knows security_id=13, it calls:                │
│     get_market_quote({"IDX_I": [13]})                           │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 13. Repeat Steps 6-10 for Second Tool Call                       │
│     - Execute get_market_quote                                  │
│     - Get market data from DhanHQ                               │
│     - Format and return result                                  │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 14. LLM: Final Response                                          │
│     After receiving tool results, LLM generates final answer:   │
│     "The current price of NIFTY 50 is ₹24,500.25..."           │
└────────────────────┬──────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│ 15. BACKEND: Return to Frontend                                  │
│     {                                                            │
│       "response": "The current price of NIFTY 50 is...",       │
│       "tool_calls": [                                            │
│         {                                                        │
│           "tool": "search_instruments",                         │
│           "status": "success",                                  │
│           "args": {...}                                         │
│         },                                                       │
│         {                                                        │
│           "tool": "get_market_quote",                           │
│           "status": "success",                                  │
│           "args": {...}                                         │
│         }                                                       │
│       ]                                                          │
│     }                                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Tool Definitions (`tools.py`)

Tools are defined in OpenAI function calling format:

```python
DHANHQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_instruments",
            "description": "Search for instruments by name or symbol",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "..."},
                    "instrument_type": {"type": "string", "enum": [...]}
                },
                "required": ["query"]
            }
        }
    },
    # ... more tools
]
```

### 2. Tool Execution (`tool_executor.py`)

The `execute_tool()` function routes tool calls:

```python
async def execute_tool(function_name, function_args, access_token):
    # Try new tool router first
    tool = get_tool(function_name)  # From agent.tool_registry
    if tool:
        return await router_execute_tool(function_name, function_args, access_token)

    # Fall back to legacy execution
    if function_name == "search_instruments":
        return await search_instruments(...)
    elif function_name == "get_market_quote":
        return trading_service.get_market_quote(...)
    # ...
```

### 3. Agentic Loop (`main.py`)

The agentic loop allows multiple rounds of tool calls:

```python
# First round: LLM makes tool calls
if "tool_calls" in message:
    # Execute tools
    tool_results = []
    for tool_call in message["tool_calls"]:
        result = await execute_tool(...)
        tool_results.append(result)

    # Send results back to LLM
    messages.append(message)  # Assistant message with tool_calls
    messages.extend(tool_results)  # Tool results

    # AGENTIC LOOP: Allow LLM to make more tool calls
    while iteration < max_iterations:
        # Get LLM response with tool results
        next_message = await llm_api_call(messages, tools)

        if "tool_calls" in next_message:
            # Execute more tools
            # Add results to messages
            # Continue loop
        else:
            # LLM has final answer
            return final_response
```

## Example: Complete Tool Call Flow

### User Query
```
"What's the current price of NIFTY?"
```

### Step 1: LLM Decides to Use Tools
```json
{
  "tool_calls": [
    {
      "id": "call_1",
      "function": {
        "name": "search_instruments",
        "arguments": "{\"query\":\"NIFTY\",\"instrument_type\":\"INDEX\"}"
      }
    }
  ]
}
```

### Step 2: Backend Executes Tool
```python
result = await execute_tool(
    "search_instruments",
    {"query": "NIFTY", "instrument_type": "INDEX"},
    access_token
)
# Returns: {"success": true, "data": {"instruments": [...]}}
```

### Step 3: Format Result for LLM
```json
{
  "role": "tool",
  "tool_call_id": "call_1",
  "name": "search_instruments",
  "content": "✅ Success!\n\nFound NIFTY 50:\n- Security ID: 13\n- Exchange: IDX_I\n..."
}
```

### Step 4: LLM Makes Second Tool Call
```json
{
  "tool_calls": [
    {
      "id": "call_2",
      "function": {
        "name": "get_market_quote",
        "arguments": "{\"securities\":{\"IDX_I\":[13]}}"
      }
    }
  ]
}
```

### Step 5: Execute Second Tool
```python
result = await execute_tool(
    "get_market_quote",
    {"securities": {"IDX_I": [13]}},
    access_token
)
# Returns market quote data
```

### Step 6: LLM Generates Final Answer
```
"The current price of NIFTY 50 is ₹24,500.25..."
```

## Code Locations

- **Tool Definitions**: `app/backend/tools.py` - `DHANHQ_TOOLS`
- **Tool Execution**: `app/backend/tool_executor.py` - `execute_tool()`
- **Agentic Loop**: `app/backend/main.py` - `generate_openai_response()` (lines 915-1200)
- **Tool Router**: `app/backend/agent/tool_router.py` - Routes to registered tools
- **Tool Registry**: `app/backend/agent/tool_registry.py` - Manages tool registration

## Important Notes

1. **Tool Choice**: The LLM decides when to use tools based on:
   - System prompt instructions
   - `tool_choice` parameter ("auto" or "required")
   - User query content

2. **Agentic Loop**: The system supports up to 5 iterations, allowing the LLM to:
   - Make sequential tool calls
   - Use results from one tool to call another
   - Build up information before answering

3. **Error Handling**: If a tool fails:
   - Error message is sent back to LLM
   - LLM can try alternative approaches
   - User sees error in execution flow sidebar

4. **Streaming**: Tool calls are sent to frontend as they happen:
   - `{"type": "tool_calls", "tool_calls": [...]}`
   - Frontend displays in Execution Flow sidebar
   - Final response streams after all tools complete

## Testing Tool Calls

You can test tool calls by:

1. **Check Backend Logs**:
   ```
   [get_market_quote] Calling with securities: {'IDX_I': [13]}
   [execute_tool] Executing: get_market_quote
   [agentic_loop] Iteration 1/5
   ```

2. **Check Frontend Execution Flow**:
   - Shows "Analyzing request"
   - Shows tool execution steps
   - Shows "Generating response"

3. **Direct API Test**:
   ```bash
   curl -X POST http://localhost:8001/api/chat/stream \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is the price of NIFTY?",
       "access_token": "your_token"
     }'
   ```

