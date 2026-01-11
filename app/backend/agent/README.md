# Trading Agent Tool Layer

This directory contains the **tool layer architecture** for the trading AI assistant.

## Architecture Overview

```
React Chat UI
     ↓
FastAPI /chat
     ↓
Agent Orchestrator (main.py)
     ↓
Tool Router (tool_router.py)
     ↓
Tool Registry (tool_registry.py)
     ↓
Concrete Tools (tools/*.py)
     ↓
DhanHQ-py / Market Data / Orders
```

## Core Principles

1. **Single Responsibility**: Each tool does one thing well
2. **Stateless/Idempotent**: Tools can be retried safely
3. **JSON Input/Output**: Compatible with LLM function calling
4. **Guarded**: Safety checks prevent dangerous operations
5. **Deterministic**: Same input = same output

## Directory Structure

```
agent/
├── __init__.py
├── tools/
│   ├── __init__.py
│   ├── base.py          # Base Tool class
│   ├── find_instrument.py
│   ├── get_quote.py
│   ├── get_historical_data.py
│   └── analyze_market.py
├── tool_registry.py     # Central tool registry
├── tool_router.py       # Tool execution router
└── README.md
```

## Adding a New Tool

1. Create a new file in `tools/` directory
2. Inherit from `Tool` base class
3. Implement `run()` method
4. Register in `tool_registry.py`

Example:

```python
from app.agent.tools.base import Tool

class MyNewTool(Tool):
    name = "my_new_tool"
    description = "What this tool does"
    input_schema = {...}
    output_schema = {...}

    def run(self, access_token=None, **kwargs):
        # Tool logic here
        return {"success": True, "data": ...}
```

Then register in `tool_registry.py`:

```python
from app.agent.tools.my_new_tool import MyNewTool

def initialize_registry():
    ...
    register_tool(MyNewTool())
```

## Tool Categories

### Market Data Tools (Read-Only)
- `find_instrument`: Resolve symbol to security_id
- `get_quote`: Get real-time market quotes
- `get_historical_data`: Get historical OHLCV data
- `analyze_market`: Composite analysis tool

### Future Tools (To Be Added)
- `get_option_chain`: Options chain data
- `get_positions`: Current positions
- `get_holdings`: Portfolio holdings
- `calculate_position_size`: Risk calculation
- `validate_trade_risk`: Trade validation
- `place_order`: Order execution (gated)

## Backward Compatibility

The system maintains backward compatibility with legacy tool names:
- `search_instruments` → `find_instrument`
- `get_market_quote` → `get_quote`

Legacy tools in `tool_executor.py` are still supported for tools not yet migrated.

## Usage

Tools are automatically exposed to the LLM via `tools.py`:

```python
from app.agent.tool_registry import get_tool_specs

tools = get_tool_specs()  # Returns OpenAI function calling format
```

Execution happens through `tool_router.py`:

```python
from app.agent.tool_router import execute_tool

result = await execute_tool(
    tool_name="find_instrument",
    tool_args={"query": "NIFTY"},
    access_token=token
)
```

## Safety

All tools have a `safety` attribute:
- `read_only`: True for data fetching tools
- `requires_confirmation`: True for execution tools

Execution tools (like `place_order`) must be explicitly enabled and gated.

