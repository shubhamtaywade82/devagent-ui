from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple


def today_yyyy_mm_dd() -> str:
    return date.today().strftime("%Y-%m-%d")


def days_ago_yyyy_mm_dd(days: int) -> str:
    return (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")


def extract_symbol_guess(user_query: str) -> Optional[str]:
    """
    Minimal extraction of a likely symbol from a user query.
    If this can't confidently find a token, returns None and the planner should ask the user.
    """
    if not user_query:
        return None
    q = user_query.strip()
    if not q:
        return None

    # Fast-path for common indices / multi-word names.
    upper = q.upper()
    if "BANKNIFTY" in upper or "BANK NIFTY" in upper:
        return "BANKNIFTY"
    if "NIFTY" in upper:
        return "NIFTY"
    if "SENSEX" in upper:
        return "SENSEX"

    # Otherwise, take the first alphabetic token (e.g., RELIANCE, TCS, INFY).
    tokens = []
    cur = []
    for ch in upper:
        if "A" <= ch <= "Z":
            cur.append(ch)
        else:
            if cur:
                tokens.append("".join(cur))
                cur = []
    if cur:
        tokens.append("".join(cur))

    # Avoid generic words.
    stop = {
        "CAN", "I", "BUY", "TODAY", "PLEASE", "PRICE", "QUOTE", "ANALYZE", "ANALYSIS",
        "SWING", "INTRADAY", "SCALP", "OPTION", "OPTIONS", "CE", "PE", "CALL", "PUT",
        "GOOD", "FOR", "IS", "THE", "A", "OF", "TO",
    }
    for tok in tokens:
        if tok and tok not in stop and len(tok) >= 3:
            return tok
    return None


def is_index_symbol(symbol: str) -> bool:
    u = (symbol or "").upper()
    return u in {"NIFTY", "BANKNIFTY", "SENSEX"} or "NIFTY" in u or "SENSEX" in u


def sma(values: List[float], period: int) -> Optional[float]:
    if period <= 0 or len(values) < period:
        return None
    window = values[-period:]
    return sum(window) / float(period)


def vwap(candles: List[Dict[str, Any]]) -> Optional[float]:
    """
    VWAP from intraday candles.
    Uses typical price (H+L+C)/3 weighted by volume.
    """
    num = 0.0
    den = 0.0
    for c in candles:
        try:
            h = float(c.get("high"))
            l = float(c.get("low"))
            cl = float(c.get("close"))
            vol = float(c.get("volume") or 0.0)
        except Exception:
            continue
        tp = (h + l + cl) / 3.0
        num += tp * vol
        den += vol
    if den <= 0:
        return None
    return num / den


def recent_swing_low(candles: List[Dict[str, Any]], lookback: int) -> Optional[float]:
    lows: List[float] = []
    for c in candles[-lookback:]:
        try:
            lows.append(float(c.get("low")))
        except Exception:
            continue
    return min(lows) if lows else None


def recent_swing_high(candles: List[Dict[str, Any]], lookback: int) -> Optional[float]:
    highs: List[float] = []
    for c in candles[-lookback:]:
        try:
            highs.append(float(c.get("high")))
        except Exception:
            continue
    return max(highs) if highs else None


def classify_htf_bias(daily_candles: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Returns (htf_bias, allowed_direction):
    - BULLISH -> CE_ONLY / BUY_ONLY
    - BEARISH -> PE_ONLY
    - RANGE   -> NO_TRADE
    """
    closes: List[float] = []
    for c in daily_candles:
        try:
            closes.append(float(c.get("close")))
        except Exception:
            continue

    if len(closes) < 60:
        # Not enough data to be confident; treat as range to fail safe.
        return "RANGE", "NO_TRADE"

    s20 = sma(closes, 20)
    s50 = sma(closes, 50)
    last = closes[-1]
    if s20 is None or s50 is None:
        return "RANGE", "NO_TRADE"

    if s20 > s50 and last > s20:
        return "BULLISH", "CE_ONLY"
    if s20 < s50 and last < s20:
        return "BEARISH", "PE_ONLY"
    return "RANGE", "NO_TRADE"


def classify_ltf_structure(intraday_candles: List[Dict[str, Any]]) -> Tuple[str, bool]:
    """
    Returns (ltf_structure, entry_permission)
    """
    if len(intraday_candles) < 30:
        return "NEUTRAL", False

    vw = vwap(intraday_candles)
    try:
        last_close = float(intraday_candles[-1].get("close"))
    except Exception:
        return "NEUTRAL", False

    # Basic structure: last close above VWAP and making new highs recently.
    swing_h = recent_swing_high(intraday_candles, lookback=20)
    prev_swing_h = recent_swing_high(intraday_candles[:-1], lookback=20) if len(intraday_candles) > 1 else None

    bullish = (vw is not None and last_close > vw and swing_h is not None and prev_swing_h is not None and swing_h >= prev_swing_h)
    bearish = (vw is not None and last_close < vw)

    if bullish and not bearish:
        return "BULLISH", True
    if bearish and not bullish:
        return "BEARISH", True
    return "NEUTRAL", False


def risk_budget_from_account(account_context: Dict[str, Any]) -> Tuple[Optional[float], Optional[str]]:
    """
    Returns (risk_budget_amount, error_message).
    Expects:
      - capital: number
      - max_risk_per_trade: percent number (e.g. 0.5 means 0.5%)
    """
    capital = account_context.get("capital")
    max_risk_pct = account_context.get("max_risk_per_trade")
    if capital is None:
        return None, "I need account_context.capital to size risk."
    if max_risk_pct is None:
        return None, "I need account_context.max_risk_per_trade (as a % of capital) to size risk."
    try:
        cap = float(capital)
        pct = float(max_risk_pct)
    except Exception:
        return None, "account_context.capital and max_risk_per_trade must be numbers."
    if cap <= 0 or pct <= 0:
        return None, "account_context.capital and max_risk_per_trade must be > 0."
    return cap * (pct / 100.0), None

