"""Exact won domain shared by input, persistence and financial read boundaries.

Python integers are deliberately wider for intermediate arithmetic. Only stored
values and named/output monetary quantities are bounded; rates are not money.
"""

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation
from typing import Any

MAX_MONEY = 2**53 - 1
MONEY_COLUMNS = {
    'ledger_entries': ('amount_value', 'aux_amount_value'),
    'monthly_panels': ('amount_value', 'discount_amount'),
    'cash_flows': ('amount_value',),
    'card_payment_events': ('total_amount',),
    'card_payment_allocations': ('amount_value',),
}
MONEY_SETTINGS = frozenset({'scheduled_income', 'base_next_month_liquidity',
    'cash_flow_balance', 'liquidity_status', 'card_limit'})
MONEY_FIELDS = MONEY_SETTINGS | frozenset({column for columns in MONEY_COLUMNS.values() for column in columns}) | frozenset({
    'actual_amount', 'discount_override_amount', 'discount_amount', 'original_amount',
    'automatic_discount_amount', 'effective_discount_amount', 'effective_amount_value',
    'confirmed_amount_value', 'confirmed_effective_discount_amount', 'confirmed_effective_amount_value',
    'immediate_paid_amount', 'remaining_amount', 'original_total', 'immediate_paid_total',
    'discount_total', 'recorded_remaining_total', 'effective_remaining_total', 'primary_income_total',
    'scheduled_income', 'cash_flow_balance', 'remaining_liquidity', 'current_month_spendable',
    'current_spending_total', 'current_discount_total', 'card_total', 'planned_recurring_total',
    'fixed_cash_total', 'fixed_cash_processed_total', 'transfer_or_deposit_total', 'frozen_asset_total',
    'claim_original_total', 'claim_net_total', 'family_card_original_total', 'family_card_net_total',
    'visible_cash_flow_total', 'total', 'minimum_total', 'minimum_discount_total',
})


class MoneyDomainError(ValueError):
    """A financial value cannot be represented by the supported exact domain."""


def exact_money(value: object, label: str = 'money amount') -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise MoneyDomainError(f'{label} must be an exact integer money amount')
    try:
        amount = Decimal.from_float(value) if isinstance(value, float) else Decimal(str(value).strip())
    except (InvalidOperation, AttributeError):
        raise MoneyDomainError(f'{label} must be an exact integer money amount') from None
    if not amount.is_finite() or amount != amount.to_integral_value() or abs(amount) > MAX_MONEY:
        raise MoneyDomainError(f'{label} must be an exact integer within ±{MAX_MONEY} won')
    return int(amount)


def money_sum(values: Iterable[object]) -> int:
    """Accumulate in Python, without REAL promotion or SQLite int64 overflow."""
    return sum(exact_money(value) for value in values if value is not None)


def query_money_sum(conn: Any, query: str, parameters: tuple = ()) -> int:
    return money_sum(row[0] for row in conn.execute(query, parameters))


def validate_database_money(conn: Any) -> None:
    """Read-only admission, before any migration changes the source checkpoint."""
    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table, wanted in MONEY_COLUMNS.items():
        if table not in tables:
            continue
        present = {row[1] for row in conn.execute(f'PRAGMA table_info({table})')}
        columns = [column for column in wanted if column in present]
        if not columns:
            continue
        for row in conn.execute(f"SELECT {','.join(columns)} FROM {table}"):
            for column, value in zip(columns, row):
                if value is not None:
                    exact_money(value, f'{table}.{column}')
    if 'app_settings' in tables:
        for key, value in conn.execute('SELECT key,value FROM app_settings'):
            if key in MONEY_SETTINGS:
                exact_money(value, f'app_settings.{key}')


def allocation_totals(conn: Any, event_type: str, batch_id: int | None = None) -> dict[str, int]:
    query = """SELECT a.entry_payment_key,a.amount_value FROM card_payment_allocations a
               JOIN card_payment_events e ON e.id=a.payment_event_id WHERE e.event_type=?"""
    parameters: tuple = (event_type,)
    if batch_id is not None:
        query += ' AND e.batch_id=?'
        parameters += (batch_id,)
    totals: dict[str, int] = {}
    for key, value in conn.execute(query, parameters):
        totals[key] = totals.get(key, 0) + exact_money(value)
    return {key: exact_money(total, 'allocated total') for key, total in totals.items()}


def validate_money_payload(value: Any) -> None:
    """Known financial fields only; identifiers, ratios and policy metadata are not money."""
    if isinstance(value, dict):
        if isinstance(value.get('key'), str) and value['key'] in MONEY_SETTINGS and 'value' in value:
            exact_money(value['value'], f"app_settings.{value['key']}")
        for key, child in value.items():
            if key in MONEY_FIELDS and child is not None:
                exact_money(child, key)
            elif isinstance(child, (dict, list)):
                validate_money_payload(child)
    elif isinstance(value, list):
        for child in value:
            validate_money_payload(child)
