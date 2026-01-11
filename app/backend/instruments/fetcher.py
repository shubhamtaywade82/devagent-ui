import csv
from io import StringIO
from typing import Any, Dict, List, Optional

import httpx

BASE_URL = "https://api.dhan.co/v2/instrument"


class InstrumentFetcher:
    """
    Fetches Dhan instrument master for a given exchange segment.

    Dhan endpoint returns CSV (not JSON):
      GET https://api.dhan.co/v2/instrument/{EXCHANGE_SEGMENT}
    """

    @staticmethod
    def by_segment(exchange_segment: str, timeout_s: float = 30.0) -> List[Dict[str, Any]]:
        url = f"{BASE_URL}/{exchange_segment}"
        resp = httpx.get(url, follow_redirects=True, timeout=timeout_s)
        resp.raise_for_status()

        reader = csv.DictReader(StringIO(resp.text))
        return [InstrumentFetcher.normalize(row) for row in reader]

    @staticmethod
    def normalize(row: Dict[str, Any]) -> Dict[str, Any]:
        def fnum(val: Optional[str]) -> Optional[float]:
            if val is None:
                return None
            s = str(val).strip()
            if s == "":
                return None
            try:
                return float(s)
            except Exception:
                return None

        exch = (row.get("EXCH_ID") or "").strip() or None
        seg = (row.get("SEGMENT") or "").strip() or None

        # Keep original raw row keys too; frontend already handles these fields today.
        normalized = dict(row)
        normalized.update(
            {
                "security_id": (row.get("SECURITY_ID") or row.get("SM_SECURITY_ID") or row.get("SEM_SECURITY_ID")),
                "symbol_name": row.get("SYMBOL_NAME") or row.get("SM_SYMBOL_NAME") or row.get("SEM_SYMBOL_NAME"),
                "display_name": row.get("DISPLAY_NAME") or row.get("SEM_CUSTOM_SYMBOL"),
                "exchange": exch,
                "segment": seg,
                "exchange_segment": f"{exch}_{seg}" if exch and seg else None,
                "instrument": row.get("INSTRUMENT"),
                "series": row.get("SERIES"),
                "lot_size": fnum(row.get("LOT_SIZE") or row.get("SEM_LOT_UNITS")),
                "tick_size": fnum(row.get("TICK_SIZE") or row.get("SEM_TICK_SIZE")),
                "expiry_date": row.get("SM_EXPIRY_DATE"),
                "strike_price": fnum(row.get("STRIKE_PRICE")),
                "option_type": row.get("OPTION_TYPE"),
                "underlying_symbol": row.get("UNDERLYING_SYMBOL"),
            }
        )
        return normalized

