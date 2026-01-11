"""
Guard layer: missing-info detection + JSON Schema validation.

This runs BEFORE any tool execution. If required information is missing or invalid,
the tool call is blocked and the caller is instructed to ask the user.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


def detect_missing_fields(schema: dict, payload: dict) -> List[str]:
    required = schema.get("required", [])
    return [field for field in required if field not in payload]


def _jsonschema_validate(schema: dict, payload: dict) -> Tuple[bool, List[str]]:
    """
    Returns (is_valid, errors).
    Uses jsonschema if installed; otherwise performs a minimal required-field check.
    """
    try:
        from jsonschema import Draft7Validator  # type: ignore
    except Exception:
        missing = detect_missing_fields(schema, payload)
        if missing:
            return False, [f"Missing required field(s): {', '.join(missing)}"]
        return True, []

    validator = Draft7Validator(schema)
    errors = []
    for err in sorted(validator.iter_errors(payload), key=lambda e: e.path):
        # Create user-facing, stable messages. Prefer a field name when possible.
        path = ".".join([str(p) for p in err.path]) if err.path else None
        if path:
            errors.append(f"{path}: {err.message}")
        else:
            errors.append(err.message)
    return (len(errors) == 0), errors


def guard_tool_call(intent: str, schema: dict, payload: dict) -> Dict[str, Any]:
    """
    Guard result protocol:
    - action == "PROCEED": safe to execute tool
    - action == "ASK_USER": missing required fields; tool should not execute
    - action == "ASK_USER_INVALID": invalid fields; tool should not execute
    """
    missing = detect_missing_fields(schema, payload)
    if missing:
        return {
            "action": "ASK_USER",
            "intent": intent,
            "missing_fields": missing,
            "message": f"I need {', '.join(missing)} to proceed.",
        }

    is_valid, errors = _jsonschema_validate(schema, payload)
    if not is_valid:
        # Provide a concise single-line message plus details for debugging/LLM.
        return {
            "action": "ASK_USER_INVALID",
            "intent": intent,
            "invalid_fields": errors[:10],
            "message": "Some parameters are invalid. Please correct them and try again.",
        }

    return {"action": "PROCEED", "intent": intent}

