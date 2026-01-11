from __future__ import annotations

from typing import Any, Dict, Optional

from .models import PlannerResult
from .options_buying import OptionsBuyingPlanner
from .swing_buy import SwingBuyPlanner
from .tool_client import ToolClient


def classify_intent(user_query: str) -> str:
    q = (user_query or "").lower()
    if any(k in q for k in ["swing", "weeks", "positional"]):
        return "SWING_BUY"
    if any(k in q for k in ["option", "options", "ce", "pe", "call", "put"]):
        return "OPTIONS_BUYING"
    # Default: swing buy is safer (equity buy-only), but do not assume execution.
    return "SWING_BUY"


async def run_planner(
    *,
    user_query: str,
    account_context: Dict[str, Any],
    tools: ToolClient,
) -> PlannerResult:
    intent = classify_intent(user_query)
    if intent == "OPTIONS_BUYING":
        return await OptionsBuyingPlanner().run(user_query=user_query, account_context=account_context, tools=tools)
    return await SwingBuyPlanner().run(user_query=user_query, account_context=account_context, tools=tools)

