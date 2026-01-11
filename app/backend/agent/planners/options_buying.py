from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from .models import PlannerResult, PlannerState
from .tool_client import ToolClient
from .utils import (
    classify_htf_bias,
    classify_ltf_structure,
    days_ago_yyyy_mm_dd,
    extract_symbol_guess,
    is_index_symbol,
    recent_swing_low,
    risk_budget_from_account,
    today_yyyy_mm_dd,
)


def _pick_nearest_expiry(expiry_payload: Any) -> Optional[str]:
    """
    Best-effort extraction of the nearest expiry date from Dhan expiry_list payload.
    """
    # Common shapes:
    # - {"data": ["2026-01-30", ...]}
    # - {"data": {"data": ["..."]}}
    # - list of strings
    expiries: List[str] = []
    if isinstance(expiry_payload, list):
        expiries = [str(x) for x in expiry_payload]
    elif isinstance(expiry_payload, dict):
        if "data" in expiry_payload:
            inner = expiry_payload.get("data")
            if isinstance(inner, list):
                expiries = [str(x) for x in inner]
            elif isinstance(inner, dict):
                inner2 = inner.get("data") or inner.get("expiries") or inner.get("expiry") or inner.get("expiry_list")
                if isinstance(inner2, list):
                    expiries = [str(x) for x in inner2]
    expiries = [e for e in expiries if isinstance(e, str) and len(e) >= 8]
    if not expiries:
        return None
    # Sort ISO dates safely (YYYY-MM-DD).
    expiries_sorted = sorted(expiries)
    today = date.today().strftime("%Y-%m-%d")
    for e in expiries_sorted:
        if e >= today:
            return e
    return expiries_sorted[-1]


def _extract_underlying_ltp_from_quote(result: Dict[str, Any]) -> Optional[float]:
    """
    Extract a single LTP value from get_quote response.
    """
    # Our get_quote returns {"data": raw_api_dict, "quotes": normalized_list}
    quotes = result.get("quotes")
    if isinstance(quotes, list) and quotes:
        first = quotes[0]
        try:
            ltp = first.get("ltp")
            return float(ltp) if ltp is not None else None
        except Exception:
            return None
    return None


class OptionsBuyingPlanner:
    """
    Strict, sequential planner for options buying.
    This planner:
    - resolves underlying via find_instrument
    - computes HTF bias via daily OHLCV
    - confirms LTF structure via intraday OHLCV
    - discovers expiry via get_expiry_list
    - fetches option chain via get_option_chain
    - selects a candidate contract (best-effort)
    - emits a single decision or halts safely
    """

    async def run(self, *, user_query: str, account_context: Dict[str, Any], tools: ToolClient) -> PlannerResult:
        state = PlannerState()

        # O1 — parse intent
        underlying_symbol = extract_symbol_guess(user_query)
        if not underlying_symbol:
            return PlannerResult(
                action="ASK_USER",
                message="Which underlying should I analyze for options buying (e.g., NIFTY, BANKNIFTY, SENSEX, RELIANCE)?",
                missing_fields=["underlying_symbol"],
                state=state,
            )
        state.intent = {
            "underlying_symbol": underlying_symbol,
            "trade_type": "OPTIONS_BUYING",
            "time_horizon": "INTRADAY",
            "direction": "UNKNOWN",
        }

        # O2 — resolve underlying instrument
        inst_type = "INDEX" if is_index_symbol(underlying_symbol) else "EQUITY"
        inst_res = await tools.call("find_instrument", {"query": underlying_symbol, "instrument_type": inst_type, "limit": 1})
        if not inst_res.get("success"):
            return PlannerResult(action="NO_TRADE", message=f"Could not resolve instrument for '{underlying_symbol}': {inst_res.get('error')}", state=state)

        instruments = inst_res.get("instruments") or inst_res.get("data", {}).get("instruments")  # legacy compatibility
        if not isinstance(instruments, list) or not instruments:
            return PlannerResult(action="NO_TRADE", message=f"Could not resolve instrument for '{underlying_symbol}'.", state=state)

        inst = instruments[0]
        state.instrument = {
            "security_id": str(inst.get("security_id")),
            "exchange_segment": inst.get("exchange_segment"),
            "instrument_type": inst.get("instrument_type") or inst_type,
        }
        if not state.instrument.get("security_id") or not state.instrument.get("exchange_segment"):
            return PlannerResult(action="NO_TRADE", message="Instrument resolution returned incomplete data (missing security_id/exchange_segment).", state=state)

        # O3 — HTF bias (daily)
        daily_args = {
            "security_id": state.instrument["security_id"],
            "exchange_segment": state.instrument["exchange_segment"],
            "instrument_type": state.instrument.get("instrument_type") or inst_type,
            "from_date": days_ago_yyyy_mm_dd(60),
            "to_date": today_yyyy_mm_dd(),
        }
        daily = await tools.call("get_daily_ohlcv", daily_args)
        if not daily.get("success"):
            # If blocked by guard, surface ask-user message.
            if daily.get("action") in ["ASK_USER", "ASK_USER_INVALID"]:
                return PlannerResult(action="ASK_USER", message=daily.get("error", "Missing information to fetch daily OHLCV."), state=state)
            return PlannerResult(action="ERROR", message="Failed to fetch daily OHLCV.", error=daily.get("error"), state=state)
        daily_candles = daily.get("data") if isinstance(daily.get("data"), list) else []
        htf_bias, allowed_direction = classify_htf_bias(daily_candles)
        state.htf = {"htf_bias": htf_bias, "allowed_direction": allowed_direction}
        if allowed_direction == "NO_TRADE":
            return PlannerResult(action="NO_TRADE", message="HTF regime is RANGE/CHOP. Options buying is blocked by planner rules.", state=state)

        # O4 — LTF confirmation (intraday)
        intraday_args = {
            "security_id": state.instrument["security_id"],
            "exchange_segment": state.instrument["exchange_segment"],
            "instrument_type": state.instrument.get("instrument_type") or inst_type,
            "interval": "5",
            "from_date": today_yyyy_mm_dd(),
            "to_date": today_yyyy_mm_dd(),
        }
        intraday = await tools.call("get_intraday_ohlcv", intraday_args)
        if not intraday.get("success"):
            if intraday.get("action") in ["ASK_USER", "ASK_USER_INVALID"]:
                return PlannerResult(action="ASK_USER", message=intraday.get("error", "Missing information to fetch intraday OHLCV."), state=state)
            return PlannerResult(action="ERROR", message="Failed to fetch intraday OHLCV.", error=intraday.get("error"), state=state)
        intra_candles = intraday.get("data") if isinstance(intraday.get("data"), list) else []
        ltf_structure, entry_permission = classify_ltf_structure(intra_candles)
        state.ltf = {"ltf_structure": ltf_structure, "entry_permission": entry_permission, "interval": "5"}
        if not entry_permission:
            return PlannerResult(action="NO_TRADE", message="LTF structure does not confirm entry. Planner blocks the trade (WAIT/NO_TRADE).", state=state)

        # O5 — expiry discovery (required for option chain in this repo)
        expiry_res = await tools.call(
            "get_expiry_list",
            {"underlying_security_id": state.instrument["security_id"], "exchange_segment": state.instrument["exchange_segment"]},
        )
        expiry_date = None
        if expiry_res.get("success"):
            expiry_date = _pick_nearest_expiry(expiry_res.get("data"))
        if not expiry_date:
            return PlannerResult(
                action="ASK_USER",
                message="I couldn’t determine the expiry date for the option chain. Which expiry_date (YYYY-MM-DD) should I use?",
                missing_fields=["expiry_date"],
                state=state,
            )

        # O5 — option chain snapshot
        oc = await tools.call(
            "get_option_chain",
            {
                "underlying_security_id": state.instrument["security_id"],
                "exchange_segment": state.instrument["exchange_segment"],
                "expiry_date": expiry_date,
            },
        )
        if not oc.get("success"):
            if oc.get("action") in ["ASK_USER", "ASK_USER_INVALID"]:
                return PlannerResult(action="ASK_USER", message=oc.get("error", "Missing information to fetch option chain."), state=state)
            return PlannerResult(action="ERROR", message="Failed to fetch option chain.", error=oc.get("error"), state=state)
        state.option_chain = {"expiry_date": expiry_date, "raw": oc.get("data")}

        # Pull spot LTP to choose ATM from strikes (no hardcoded strike steps).
        quote = await tools.call("get_quote", {"securities": {state.instrument["exchange_segment"]: [int(state.instrument["security_id"])]}})
        spot = _extract_underlying_ltp_from_quote(quote) if quote.get("success") else None

        # O6 — strike selection (best-effort)
        selected = {
            "option_type": "CE" if allowed_direction == "CE_ONLY" else "PE",
            "strike": None,
            "security_id": None,
            "exchange_segment": None,
            "expiry": expiry_date,
        }
        # We can’t rely on a fixed option-chain schema, so we store raw and ask for missing parts if needed.
        # A future enhancement can parse strikes/OI/contract ids from `state.option_chain["raw"]`.
        state.selected_option = selected
        if selected["security_id"] is None:
            return PlannerResult(
                action="ASK_USER",
                message="I have the option chain, but I can’t reliably extract the option contract security_id/strike from this response shape yet. Which option contract (security_id, exchange_segment) should I analyze for LTP/risk sizing?",
                missing_fields=["option_security_id", "option_exchange_segment"],
                state=state,
            )

        # O7 — risk & sizing (strict)
        risk_budget, risk_err = risk_budget_from_account(account_context)
        if risk_err:
            return PlannerResult(action="ASK_USER", message=risk_err, missing_fields=["account_context.capital", "account_context.max_risk_per_trade"], state=state)

        # Without a reliable option LTP + lot size extraction, we can’t compute quantity safely.
        return PlannerResult(
            action="ASK_USER",
            message="To compute quantity safely, I need the option lot_size and option LTP. Provide lot_size, or allow me to add a tool to fetch contract details/lot size.",
            missing_fields=["lot_size"],
            state=state,
        )

