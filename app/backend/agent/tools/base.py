"""
Base tool class for trading agent tools

All tools must inherit from this class and implement the run method.
Tools are stateless, deterministic, and follow a strict input/output schema.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple


class Tool(ABC):
    """
    Base class for all trading agent tools.

    Tools are:
    - Single responsibility
    - Stateless or idempotent
    - JSON input/output
    - Guarded (with safety checks)
    - Deterministic
    """

    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    safety: Dict[str, Any] = {
        "read_only": True,
        "requires_confirmation": False
    }

    @abstractmethod
    def run(self, access_token: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the tool with given arguments.

        Args:
            access_token: DhanHQ access token (required for most operations)
            **kwargs: Tool-specific arguments from input_schema

        Returns:
            Dict with tool execution results matching output_schema
        """
        pass

    def validate_input(self, **kwargs) -> Tuple[bool, Optional[str]]:
        """
        Validate input arguments against input_schema.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Prefer full JSON Schema validation when available.
        try:
            from jsonschema import Draft7Validator  # type: ignore

            validator = Draft7Validator(self.input_schema)
            errors = sorted(validator.iter_errors(kwargs), key=lambda e: e.path)
            if errors:
                # Return the first error for brevity; guard layer can provide richer output.
                err = errors[0]
                path = ".".join([str(p) for p in err.path]) if err.path else None
                if path:
                    return False, f"Invalid value for '{path}': {err.message}"
                return False, f"Input validation failed: {err.message}"
            return True, None
        except Exception:
            # Fallback: minimal required-field validation.
            required = self.input_schema.get("required", [])
            for field in required:
                if field not in kwargs:
                    return False, f"Missing required field: {field}"
            return True, None

    def to_openai_spec(self) -> Dict[str, Any]:
        """
        Convert tool to OpenAI function calling format.

        Returns:
            Dict in OpenAI function calling format
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.input_schema
            }
        }

