"""
Tool Router

Routes tool execution requests to the appropriate tool handler.
This is the execution layer that sits between the LLM and tools.
"""

from typing import Dict, Any, Optional
import inspect
try:
    from agent.tool_registry import get_tool
except ImportError:
    from app.agent.tool_registry import get_tool


async def execute_tool(
    tool_name: str,
    tool_args: Dict[str, Any],
    access_token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.

    Args:
        tool_name: Name of the tool to execute (supports aliases)
        tool_args: Arguments for the tool (from LLM)
        access_token: DhanHQ access token (required for most operations)

    Returns:
        Dict with tool execution results
    """
    # Handle legacy tool name mappings
    legacy_mappings = {
        "search_instruments": "find_instrument",
        "get_market_quote": "get_quote"
    }

    # Map legacy names to new names
    actual_tool_name = legacy_mappings.get(tool_name, tool_name)

    # Also handle argument mapping for legacy tools
    if tool_name == "get_market_quote" and "securities" in tool_args:
        # get_quote expects the same format, so no mapping needed
        pass

    try:
        tool = get_tool(actual_tool_name)
    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to get tool: {str(e)}"
        }

    if not tool:
        try:
            available_tools = get_all_tool_names()
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Available tools: {', '.join(available_tools)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}. Failed to get available tools: {str(e)}"
            }

    # Validate input
    try:
        is_valid, error = tool.validate_input(**tool_args)
        if not is_valid:
            return {"success": False, "error": error or "Input validation failed"}
    except Exception as e:
        return {
            "success": False,
            "error": f"Input validation error: {str(e)}"
        }

    # Execute tool
    try:
        # Check if tool.run is async
        if inspect.iscoroutinefunction(tool.run):
            result = await tool.run(access_token=access_token, **tool_args)
        else:
            result = tool.run(access_token=access_token, **tool_args)

        # Ensure result has success field
        if not isinstance(result, dict):
            return {
                "success": False,
                "error": f"Tool returned invalid result type: {type(result)}"
            }

        # If result doesn't have success field, assume it's successful if no error
        if "success" not in result:
            result["success"] = True

        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"[tool_router] Tool execution exception: {error_trace}")
        return {
            "success": False,
            "error": f"Tool execution failed: {str(e)}"
        }


def get_all_tool_names() -> list[str]:
    """Get list of all available tool names"""
    try:
        from agent.tool_registry import get_all_tools
    except ImportError:
        from app.agent.tool_registry import get_all_tools
    tools = get_all_tools()
    return list(tools.keys())

