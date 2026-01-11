from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

PlannerAction = Literal[
    "ASK_USER",
    "NO_TRADE",
    "DECISION",
    "ERROR",
]


@dataclass
class PlannerState:
    intent: Dict[str, Any] = field(default_factory=dict)
    instrument: Dict[str, Any] = field(default_factory=dict)
    htf: Dict[str, Any] = field(default_factory=dict)
    ltf: Dict[str, Any] = field(default_factory=dict)
    option_chain: Dict[str, Any] = field(default_factory=dict)
    selected_option: Dict[str, Any] = field(default_factory=dict)
    risk: Dict[str, Any] = field(default_factory=dict)
    decision: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlannerResult:
    action: PlannerAction
    message: str
    state: PlannerState = field(default_factory=PlannerState)
    missing_fields: List[str] = field(default_factory=list)
    error: Optional[str] = None
    decision: Optional[Dict[str, Any]] = None

