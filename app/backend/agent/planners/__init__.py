"""
Deterministic planners that sit above the tool layer.

Planners are internal orchestration logic:
- They do NOT execute trades.
- They call read-only tools with strict schemas/guards.
- They halt safely on missing info or invalid market conditions.
"""

