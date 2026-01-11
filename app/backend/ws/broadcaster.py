from __future__ import annotations

import asyncio
from typing import Any, Dict, Set

from fastapi import WebSocket

from ws.market_cache import MarketCache


class MarketBroadcaster:
    def __init__(self, cache: MarketCache, interval_s: float = 0.2) -> None:
        self._cache = cache
        self._interval_s = interval_s
        self._clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._clients.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)

    async def broadcast_loop(self) -> None:
        while True:
            payload: Dict[str, Any] = {
                "type": "market_snapshot",
                "data": self._cache.snapshot(),
            }
            async with self._lock:
                clients = list(self._clients)
            for ws in clients:
                try:
                    await ws.send_json(payload)
                except Exception:
                    await self.disconnect(ws)
            await asyncio.sleep(self._interval_s)

