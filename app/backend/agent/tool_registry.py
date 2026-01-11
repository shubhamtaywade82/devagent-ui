"""
Tool Registry

Central registry for all available tools. This is the single source of truth
for what tools the agent can use.
"""

from typing import Dict, Type, Any
try:
    from agent.tools.base import Tool
    from agent.tools.find_instrument import FindInstrumentTool
    from agent.tools.get_quote import GetQuoteTool
    from agent.tools.get_historical_data import GetHistoricalDataTool
    from agent.tools.analyze_market import AnalyzeMarketTool
except ImportError:
    # Fallback for different import paths
    from app.agent.tools.base import Tool
    from app.agent.tools.find_instrument import FindInstrumentTool
    from app.agent.tools.get_quote import GetQuoteTool
    from app.agent.tools.get_historical_data import GetHistoricalDataTool
    from app.agent.tools.analyze_market import AnalyzeMarketTool


# Registry of all available tools
TOOLS: Dict[str, Tool] = {}


def register_tool(tool: Tool) -> None:
    """Register a tool in the registry"""
    TOOLS[tool.name] = tool


def get_tool(name: str) -> Tool | None:
    """Get a tool by name or alias"""
    return get_tool_by_alias(name)


def get_all_tools() -> Dict[str, Tool]:
    """Get all registered tools"""
    return TOOLS.copy()


def get_tool_specs() -> list[Dict[str, Any]]:
    """
    Get all tool specs in OpenAI function calling format.

    Returns:
        List of tool specs in OpenAI format
    """
    return [tool.to_openai_spec() for tool in TOOLS.values()]


# Tool name aliases for backward compatibility
TOOL_ALIASES = {
    "search_instruments": "find_instrument",
    "get_market_quote": "get_quote"
}


def get_tool_by_alias(name: str) -> Tool | None:
    """Get tool by name or alias"""
    # Check direct name first
    tool = TOOLS.get(name)
    if tool:
        return tool

    # Check aliases
    aliased_name = TOOL_ALIASES.get(name)
    if aliased_name:
        return TOOLS.get(aliased_name)

    return None


# Initialize registry with default tools
def initialize_registry():
    """Initialize the tool registry with all available tools"""
    register_tool(FindInstrumentTool())
    register_tool(GetQuoteTool())
    register_tool(GetHistoricalDataTool())
    register_tool(AnalyzeMarketTool())


# Auto-initialize on import
initialize_registry()

