from __future__ import annotations

from typing import Any, Dict, Optional, Protocol


class ToolClient(Protocol):
    async def call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]: ...


class RouterToolClient:
    """
    Calls tools through the existing agent tool router (so guard/schema enforcement applies).
    """

    def __init__(self, access_token: Optional[str] = None):
        self._access_token = access_token

    async def call(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        try:
            from agent.tool_router import execute_tool
        except ImportError:
            from app.agent.tool_router import execute_tool

        return await execute_tool(tool_name=tool_name, tool_args=tool_args, access_token=self._access_token)

