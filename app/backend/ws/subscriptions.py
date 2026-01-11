from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple


FeedMode = Literal["Quote", "Full"]


@dataclass(frozen=True)
class Subscription:
    exchange_segment: str  # e.g. "IDX_I", "NSE_EQ"
    security_id: str
    mode: FeedMode = "Quote"


class SubscriptionManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: Dict[str, Subscription] = {}
        self._version = 0

    @property
    def version(self) -> int:
        with self._lock:
            return self._version

    def add(self, exchange_segment: str, security_id: str, mode: FeedMode = "Quote") -> None:
        key = f"{exchange_segment}:{security_id}"
        with self._lock:
            prev = self._subs.get(key)
            next_sub = Subscription(exchange_segment=exchange_segment, security_id=str(security_id), mode=mode)
            if prev == next_sub:
                return
            self._subs[key] = next_sub
            self._version += 1

    def remove(self, exchange_segment: str, security_id: str) -> None:
        key = f"{exchange_segment}:{security_id}"
        with self._lock:
            if key in self._subs:
                del self._subs[key]
                self._version += 1

    def list(self) -> List[Subscription]:
        with self._lock:
            return list(self._subs.values())

    def keys(self) -> List[str]:
        with self._lock:
            return list(self._subs.keys())

