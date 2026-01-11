from __future__ import annotations

import threading
from typing import Any, Dict


class MarketCache:
    """
    Thread-safe in-memory cache of latest ticks keyed by {exchange_segment}:{security_id}.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, Dict[str, Any]] = {}

    def update(self, key: str, tick: Dict[str, Any]) -> None:
        with self._lock:
            self._data[key] = tick

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._data)

