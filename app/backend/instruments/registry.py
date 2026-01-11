from __future__ import annotations

import threading
from typing import Any, Dict, Iterable, List, Optional

from instruments.fetcher import InstrumentFetcher


class InstrumentRegistry:
    """
    In-memory registry for fast symbol -> instrument lookup.

    This is intentionally separate from the Mongo "instrument master" used elsewhere;
    this registry is meant for low-latency runtime subscription orchestration.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_segment: Dict[str, List[Dict[str, Any]]] = {}
        self._symbol_index: Dict[str, Dict[str, Any]] = {}
        self._last_error: Optional[str] = None

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    def load_segment(self, exchange_segment: str, rows: List[Dict[str, Any]]) -> None:
        with self._lock:
            self._by_segment[exchange_segment] = rows
            for r in rows:
                # Prefer underlying_symbol when present (useful for derivatives),
                # otherwise fall back to symbol_name.
                sym = (r.get("underlying_symbol") or r.get("symbol_name") or r.get("SYMBOL_NAME") or "").strip()
                if not sym:
                    continue
                key = f"{exchange_segment}:{sym.upper()}"
                self._symbol_index[key] = r

    def preload(self, exchange_segments: Iterable[str], timeout_s: float = 30.0) -> None:
        """
        Best-effort preload. If a segment fails, we keep error state and continue.
        Control-plane endpoints can report last_error to the UI.
        """
        last_err: Optional[str] = None
        for seg in exchange_segments:
            try:
                rows = InstrumentFetcher.by_segment(seg, timeout_s=timeout_s)
                self.load_segment(seg, rows)
            except Exception as e:  # noqa: BLE001 - boundary layer
                last_err = f"failed to preload {seg}: {e}"
        self._last_error = last_err

    def find(self, exchange_segment: str, symbol: str) -> Optional[Dict[str, Any]]:
        key = f"{exchange_segment}:{(symbol or '').upper()}"
        with self._lock:
            return self._symbol_index.get(key)

    def find_anywhere(self, symbol: str) -> Optional[Dict[str, Any]]:
        suffix = f":{(symbol or '').upper()}"
        with self._lock:
            for k, inst in self._symbol_index.items():
                if k.endswith(suffix):
                    return inst
        return None

    def search(self, query: str, exchange_segment: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        q = (query or "").strip().upper()
        if len(q) < 2:
            return []
        out: List[Dict[str, Any]] = []
        with self._lock:
            if exchange_segment:
                rows = self._by_segment.get(exchange_segment, [])
                for r in rows:
                    sym = (r.get("symbol_name") or r.get("SYMBOL_NAME") or "").upper()
                    disp = (r.get("display_name") or r.get("DISPLAY_NAME") or "").upper()
                    if q in sym or q in disp:
                        out.append(r)
                        if len(out) >= limit:
                            break
            else:
                # Scan index (already de-duplicated per exchange_segment:symbol key)
                for k, r in self._symbol_index.items():
                    if q in k:
                        out.append(r)
                        if len(out) >= limit:
                            break
        return out

