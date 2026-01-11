"""
Canonical, reusable JSON Schemas (agent-enforced contracts).

These are intentionally strict and are meant to be shared across tools.
Do NOT duplicate per-tool schemas; tools should reference these.
"""

from __future__ import annotations

DATE_YYYY_MM_DD_PATTERN = r"^\d{4}-\d{2}-\d{2}$"

# Exchange segment values used across this codebase.
# Note: Some external docs use NSE_FNO / BSE_FNO / MCX_COMM; this repo historically uses NSE_FO / BSE_FO / MCX_COM.
# We accept both spellings to avoid breaking integrations, but tools SHOULD emit the canonical values used by APIs.
EXCHANGE_SEGMENT_ENUM = [
    "NSE_EQ",
    "BSE_EQ",
    "IDX_I",
    "NSE_FO",
    "BSE_FO",
    "MCX_COM",
    "NCDEX_COM",
    # Common aliases (accepted input; normalized downstream if needed)
    "NSE_FNO",
    "BSE_FNO",
    "MCX_COMM",
]

INSTRUMENT_TYPE_ENUM = [
    # Canonical values used throughout the repo/tooling
    "EQUITY",
    "INDEX",
    "FUTURES",
    "OPTIONS",
    # Aliases / future-proofing (accepted)
    "FUT",
    "OPT",
]

OPTION_TYPE_ENUM = ["CE", "PE"]

INTRADAY_INTERVAL_ENUM = ["1", "5", "15", "25", "60"]

MarketQuoteSchema: dict = {
    "type": "object",
    "properties": {
        "securities": {
            "type": "object",
            "description": "Map of exchange_segment -> list of security_id(s).",
            "propertyNames": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
            "additionalProperties": {
                "type": "array",
                "items": {"type": "integer"},
            },
        }
    },
    "required": ["securities"],
    "additionalProperties": True,
}


InstrumentContextSchema: dict = {
    "type": "object",
    "properties": {
        "security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
        "instrument_type": {"type": "string", "enum": INSTRUMENT_TYPE_ENUM},
    },
    "required": ["security_id", "exchange_segment"],
    "additionalProperties": True,
}


IntradayOHLCVSchema: dict = {
    "type": "object",
    "properties": {
        "security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
        "instrument_type": {"type": "string", "enum": INSTRUMENT_TYPE_ENUM},
        "interval": {"type": "string", "enum": INTRADAY_INTERVAL_ENUM},
        "from_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
        "to_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
    },
    "required": [
        "security_id",
        "exchange_segment",
        "instrument_type",
        "interval",
        "from_date",
        "to_date",
    ],
    "additionalProperties": True,
}


DailyOHLCVSchema: dict = {
    "type": "object",
    "properties": {
        "security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
        "instrument_type": {"type": "string", "enum": INSTRUMENT_TYPE_ENUM},
        "from_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
        "to_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
    },
    "required": [
        "security_id",
        "exchange_segment",
        "instrument_type",
        "from_date",
        "to_date",
    ],
    "additionalProperties": True,
}


# Minimal option-chain context (used for expiry discovery or upstream resolution).
OptionChainSchema: dict = {
    "type": "object",
    "properties": {
        "underlying_security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": ["IDX_I", "NSE_FO", "BSE_FO", "NSE_FNO", "BSE_FNO"]},
    },
    "required": ["underlying_security_id", "exchange_segment"],
    "additionalProperties": True,
}


# Concrete option-chain fetch requires an expiry (DhanHQ API requirement).
OptionChainWithExpirySchema: dict = {
    "allOf": [
        OptionChainSchema,
        {
            "type": "object",
            "properties": {
                "expiry_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
            },
            "required": ["expiry_date"],
        },
    ]
}

ExpiryListSchema: dict = {
    "type": "object",
    "properties": {
        "underlying_security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
    },
    "required": ["underlying_security_id", "exchange_segment"],
    "additionalProperties": True,
}


OptionContractSchema: dict = {
    "type": "object",
    "properties": {
        "security_id": {"type": ["string", "integer"]},
        "exchange_segment": {"type": "string", "enum": EXCHANGE_SEGMENT_ENUM},
        "option_type": {"type": "string", "enum": OPTION_TYPE_ENUM},
        "strike_price": {"type": "number"},
        "expiry_date": {"type": "string", "pattern": DATE_YYYY_MM_DD_PATTERN},
    },
    "required": ["security_id", "exchange_segment"],
    "additionalProperties": True,
}

