from __future__ import annotations

import os
import threading
import time
from typing import Any, Dict, Optional

from ws.market_cache import MarketCache
from ws.subscriptions import SubscriptionManager, Subscription


class DhanMarketDataDaemon:
    """
    Singleton-style daemon:
      - maintains ONE Dhan WebSocket connection (via dhanhq.marketfeed.DhanFeed)
      - restarts the feed when subscription set changes
      - writes latest ticks into MarketCache
    """

    def __init__(self, subs: SubscriptionManager, cache: MarketCache) -> None:
        self._subs = subs
        self._cache = cache
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

        self._feed = None
        self._feed_thread: Optional[threading.Thread] = None
        self._drain_thread: Optional[threading.Thread] = None
        self._active_version: Optional[int] = None

        self._client_id = os.getenv("DHAN_CLIENT_ID")
        self._access_token = os.getenv("DHAN_ACCESS_TOKEN")
        self._enabled = bool(self._client_id and self._access_token)

        self._last_error: Optional[str] = None

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_supervisor, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._stop_current_feed()

    def _map_exchange_segment(self, exchange_segment: str) -> int:
        seg = (exchange_segment or "").upper()
        if seg == "IDX_I":
            return 0
        if seg.startswith("NSE"):
            return 1
        if seg.startswith("BSE"):
            return 2
        # Fallback to NSE
        return 1

    def _map_mode(self, mode: str) -> Any:
        # Import lazily so backend can start even if dhanhq is missing/misinstalled.
        from dhanhq.marketfeed import Quote, Full  # type: ignore

        if (mode or "").lower() == "full":
            return Full
        return Quote

    def _build_instruments(self, subs: list[Subscription]) -> list[tuple]:
        out = []
        for s in subs:
            exch = self._map_exchange_segment(s.exchange_segment)
            out.append((exch, str(s.security_id), self._map_mode(s.mode)))
        return out

    def _stop_current_feed(self) -> None:
        try:
            if self._feed is not None:
                # Prefer close_connection() (sync) if available.
                if hasattr(self._feed, "close_connection"):
                    try:
                        self._feed.close_connection()
                    except Exception:
                        pass
                # Some versions have disconnect() coroutine; we can't await here safely.
        finally:
            self._feed = None

    def _start_feed(self, instruments: list[tuple]) -> None:
        from dhanhq.marketfeed import DhanFeed  # type: ignore

        self._feed = DhanFeed(self._client_id, self._access_token, instruments, "v2")
        feed = self._feed

        def run_forever_thread() -> None:
            # Mirror the repo's existing pattern: dedicate a thread + event loop to run_forever().
            try:
                import asyncio

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                feed.run_forever()
            except Exception as e:  # noqa: BLE001
                self._last_error = f"feed run_forever error: {e}"
            finally:
                try:
                    loop.close()  # type: ignore[name-defined]
                except Exception:
                    pass

        def drain_thread() -> None:
            # Drain tick queue and update cache.
            while not self._stop.is_set() and self._feed is feed:
                try:
                    msg = feed.get_data()
                    if msg:
                        self._ingest(msg)
                except Exception as e:  # noqa: BLE001
                    self._last_error = f"feed get_data error: {e}"
                    time.sleep(0.25)
                time.sleep(0.01)

        self._feed_thread = threading.Thread(target=run_forever_thread, daemon=True)
        self._feed_thread.start()
        self._drain_thread = threading.Thread(target=drain_thread, daemon=True)
        self._drain_thread.start()

    def _ingest(self, msg: Any) -> None:
        """
        Normalize a variety of MarketFeed payload shapes into cache updates.
        We keep payloads mostly as-is, keyed by {exchange_segment}:{security_id} if we can infer them.
        """

        def update_one(exchange_segment: Optional[str], security_id: Optional[str], tick: Dict[str, Any]) -> None:
            if not security_id:
                return
            seg = (exchange_segment or "").strip() or "UNKNOWN"
            key = f"{seg}:{str(security_id)}"
            self._cache.update(key, tick)

        if isinstance(msg, dict):
            # Common shape: {"IDX_I": {"13": {...}}} or {"data": {...}}
            if "data" in msg and isinstance(msg["data"], dict):
                return self._ingest(msg["data"])
            # Segment->security_id->tick
            for seg, payload in msg.items():
                if isinstance(payload, dict):
                    for sid, tick in payload.items():
                        if isinstance(tick, dict):
                            update_one(seg, str(sid), {**tick, "security_id": str(sid), "exchange_segment": seg})
                elif isinstance(payload, list):
                    for tick in payload:
                        if isinstance(tick, dict):
                            sid = tick.get("security_id") or tick.get("securityId") or tick.get("SECURITY_ID")
                            update_one(seg, str(sid) if sid is not None else None, {**tick, "exchange_segment": seg})
            return

        if isinstance(msg, list):
            for tick in msg:
                if isinstance(tick, dict):
                    seg = tick.get("exchange_segment") or tick.get("ExchangeSegment") or tick.get("segment")
                    sid = tick.get("security_id") or tick.get("securityId") or tick.get("SECURITY_ID")
                    update_one(str(seg) if seg is not None else None, str(sid) if sid is not None else None, tick)
            return

    def _run_supervisor(self) -> None:
        """
        Supervises subscription changes and rebuilds the feed accordingly.
        """
        if not self._enabled:
            self._last_error = "DHAN_ACCESS_TOKEN not set; market daemon disabled"
            return

        while not self._stop.is_set():
            try:
                v = self._subs.version
                subs = self._subs.list()

                if not subs:
                    # No subscriptions -> stop feed and idle.
                    if self._feed is not None:
                        self._stop_current_feed()
                        self._active_version = None
                    time.sleep(0.25)
                    continue

                if self._active_version != v:
                    # Rebuild required.
                    self._stop_current_feed()
                    instruments = self._build_instruments(subs)
                    self._start_feed(instruments)
                    self._active_version = v

                time.sleep(0.25)
            except Exception as e:  # noqa: BLE001
                self._last_error = f"daemon supervisor error: {e}"
                time.sleep(1.0)

