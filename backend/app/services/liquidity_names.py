from __future__ import annotations


LIQUIDITY_SETTING_DEFAULTS = {
    "scheduled_income": "400000",
    "cash_flow_balance": "0",
}

LEGACY_LIQUIDITY_SETTING_KEYS = {
    "base_next_month_liquidity": "scheduled_income",
    "liquidity_status": "cash_flow_balance",
}

LIQUIDITY_LABEL_DEFAULTS = {
    "summary_cash_flow_balance_label": "현금흐름 반영액",
    "summary_remaining_liquidity_label": "잔여 유동성",
}

LEGACY_LIQUIDITY_LABEL_KEYS = {
    "summary_liquidity_status_label": "summary_cash_flow_balance_label",
    "summary_next_month_liquidity_label": "summary_remaining_liquidity_label",
}

LEGACY_DEFAULT_LABEL_VALUES = {
    "summary_liquidity_status_label": {
        "유동성 현황": "현금흐름 반영액",
        "현금흐름 반영액": "현금흐름 반영액",
    },
    "summary_next_month_liquidity_label": {
        "익월 유동성": "잔여 유동성",
        "잔여 유동성": "잔여 유동성",
    },
}


def normalized_legacy_label_value(key: str, value: str) -> str:
    return LEGACY_DEFAULT_LABEL_VALUES.get(key, {}).get(value, value)
