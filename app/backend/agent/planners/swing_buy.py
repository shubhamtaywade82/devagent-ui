from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import PlannerResult, PlannerState
from .tool_client import ToolClient
from .utils import (
    days_ago_yyyy_mm_dd,
    extract_symbol_guess,
    risk_budget_from_account,
    sma,
    today_yyyy_mm_dd,
)


def _extract_closes(daily_candles: List[Dict[str, Any]]) -> List[float]:
    closes: List[float] = []
    for c in daily_candles:
        try:
            closes.append(float(c.get("close")))
        except Exception:
            continue
    return closes


class SwingBuyPlanner:
    """
    Strict, sequential planner for swing buying (stocks only).
    Uses daily OHLCV to:
    - validate HTF trend
    - derive a conservative entry/SL/target plan
    - size position from account risk budget
    """

    async def run(self, *, user_query: str, account_context: Dict[str, Any], tools: ToolClient) -> PlannerResult:
        state = PlannerState()

        # S1 — parse intent
        symbol = extract_symbol_guess(user_query)
        if not symbol:
            return PlannerResult(
                action="ASK_USER",
                message="Which stock symbol should I analyze for swing buying (e.g., RELIANCE, TCS, INFY)?",
                missing_fields=["symbol"],
                state=state,
            )
        state.intent = {"symbol": symbol, "trade_type": "SWING_BUY"}

        # S2 — resolve instrument
        inst_res = await tools.call("find_instrument", {"query": symbol, "instrument_type": "EQUITY", "limit": 1})
        if not inst_res.get("success"):
            return PlannerResult(action="NO_TRADE", message=f"Could not resolve instrument for '{symbol}': {inst_res.get('error')}", state=state)

        instruments = inst_res.get("instruments") or inst_res.get("data", {}).get("instruments")
        if not isinstance(instruments, list) or not instruments:
            return PlannerResult(action="NO_TRADE", message=f"Could not resolve instrument for '{symbol}'.", state=state)

        inst = instruments[0]
        state.instrument = {
            "security_id": str(inst.get("security_id")),
            "exchange_segment": inst.get("exchange_segment"),
            "instrument_type": "EQUITY",
        }
        if not state.instrument.get("security_id") or not state.instrument.get("exchange_segment"):
            return PlannerResult(action="NO_TRADE", message="Instrument resolution returned incomplete data (missing security_id/exchange_segment).", state=state)

        # S3 — HTF trend filter (daily, 6M)
        daily = await tools.call(
            "get_daily_ohlcv",
            {
                "security_id": state.instrument["security_id"],
                "exchange_segment": state.instrument["exchange_segment"],
                "instrument_type": "EQUITY",
                "from_date": days_ago_yyyy_mm_dd(180),
                "to_date": today_yyyy_mm_dd(),
            },
        )
        if not daily.get("success"):
            if daily.get("action") in ["ASK_USER", "ASK_USER_INVALID"]:
                return PlannerResult(action="ASK_USER", message=daily.get("error", "Missing information to fetch daily OHLCV."), state=state)
            return PlannerResult(action="ERROR", message="Failed to fetch daily OHLCV.", error=daily.get("error"), state=state)

        daily_candles = daily.get("data") if isinstance(daily.get("data"), list) else []
        closes = _extract_closes(daily_candles)
        if len(closes) < 60:
            return PlannerResult(action="NO_TRADE", message="Not enough daily OHLCV data to validate a swing trend safely.", state=state)

        s20 = sma(closes, 20)
        s50 = sma(closes, 50)
        last = closes[-1]
        if s20 is None or s50 is None:
            return PlannerResult(action="NO_TRADE", message="Could not compute trend filters (insufficient data).", state=state)

        uptrend = s20 > s50 and last > s20
        state.htf = {"trend": "UPTREND" if uptrend else "NOT_UPTREND", "swing_allowed": bool(uptrend)}
        if not uptrend:
            return PlannerResult(action="NO_TRADE", message="HTF trend filter failed (not in a clear uptrend). Swing buy is blocked.", state=state)

        # S4/S5 — setup + volume confirmation (minimal, deterministic)
        # For now: treat as pullback-buy if last close is within 3% above SMA20 and volume is not collapsing.
        try:
            last_close = float(last)
            pullback_ok = last_close <= (s20 * 1.03)
        except Exception:
            pullback_ok = False

        # Volume confirmation: require at least some non-zero volume in recent candles
        recent_vols = []
        for c in daily_candles[-20:]:
            try:
                recent_vols.append(float(c.get("volume") or 0.0))
            except Exception:
                continue
        volume_ok = sum(recent_vols) > 0

        state.ltf = {
            "setup_type": "PULLBACK_BUY" if pullback_ok else "BREAKOUT_BUY",
            "volume_confirmation": bool(volume_ok),
        }
        if not volume_ok:
            return PlannerResult(action="NO_TRADE", message="Volume confirmation failed. Swing buy is blocked.", state=state)

        # S6 — risk & sizing (strict)
        risk_budget, risk_err = risk_budget_from_account(account_context)
        if risk_err:
            return PlannerResult(action="ASK_USER", message=risk_err, missing_fields=["account_context.capital", "account_context.max_risk_per_trade"], state=state)

        # Entry/SL/Target from recent daily range (conservative):
        highs = []
        lows = []
        for c in daily_candles[-20:]:
            try:
                highs.append(float(c.get("high")))
                lows.append(float(c.get("low")))
            except Exception:
                continue
        if not highs or not lows:
            return PlannerResult(action="NO_TRADE", message="Could not derive key levels from daily OHLCV.", state=state)

        entry = last_close
        stop = min(lows)
        if stop >= entry:
            return PlannerResult(action="NO_TRADE", message="Derived stop-loss is not below entry; cannot form a valid swing plan.", state=state)
        risk_per_share = entry - stop

        # 2R target
        target = entry + 2.0 * risk_per_share
        rr = (target - entry) / risk_per_share if risk_per_share > 0 else 0.0
        if rr < 2.0:
            return PlannerResult(action="NO_TRADE", message="RR < 2.0; swing buy is blocked by planner rules.", state=state)

        qty = int(risk_budget // risk_per_share) if risk_per_share > 0 else 0
        if qty <= 0:
            return PlannerResult(action="NO_TRADE", message="Risk budget is too small for even 1 share given the derived stop-loss.", state=state)

        position_value = qty * entry
        try:
            capital = float(account_context.get("capital"))
            pct = (position_value / capital) * 100.0 if capital > 0 else None
        except Exception:
            pct = None

        state.risk = {
            "quantity": qty,
            "risk_budget": risk_budget,
            "risk_per_share": risk_per_share,
            "rr_ratio": rr,
        }

        # S7 — final decision
        decision = {
            "trade_type": "SWING_BUY",
            "symbol": symbol,
            "entry_zone": f"{entry:.2f} (market) ± 0.5%",
            "stop_loss": round(stop, 2),
            "target": round(target, 2),
            "holding_period": "2–4 weeks",
            "position_size": f"{pct:.2f}% capital" if pct is not None else "N/A",
            "quantity": qty,
            "confidence": 0.7,
            "trade_permission": "YES",
        }
        state.decision = decision
        return PlannerResult(action="DECISION", message="Swing buy plan generated.", decision=decision, state=state)

