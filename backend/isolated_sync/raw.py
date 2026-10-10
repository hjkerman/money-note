"""Explicit structural=1 raw row admission. No financial projection formulas.

Column/type contract mirrors Snapshot v7/B-2, not SQLite's permissive affinity.
The descriptor is checked against the migrated schema in differential tests.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import re

from isolated_sync.canonical import Key, MAX_MONEY, decode_c1, encode, fail, integer, money, row_hash


TABLES = ("ledger_entries", "monthly_panels", "cash_flows", "card_payment_batches",
          "card_payment_batch_items", "card_payment_events", "card_payment_allocations",
          "card_payment_deferrals", "notification_candidate_registrations", "app_settings", "app_labels")
SENSITIVE = frozenset({"share_pin_hash", "share_pin_is_default"})
MONEY_SETTINGS = frozenset({"scheduled_income", "cash_flow_balance", "card_limit"})
MONEY_SETTING_FIELDS = MONEY_SETTINGS | {"base_next_month_liquidity", "liquidity_status"}


def _shape(text):
    return dict(item.split(":") for item in text.split())


SHAPES = {
    "ledger_entries": _shape("""id:i book_section:s entry_kind:s entry_date:?d date_label:?s group_label:?s
        title:s usage_place:?s usage_item:?s amount_value:?n amount_expr:?s aux_amount_value:?n
        aux_amount_expr:?s extra_value:?s sort_order:i due_day:?i confirmed_at:?s confirmed_month:?m
        source_planned_entry_id:?i spending_category:?s payment_key:?s discount_override:i created_at:s updated_at:s"""),
    "monthly_panels": _shape("""id:i month:m panel_type:s title:s spent_on:?d amount_value:?n discount_amount:n
        discount_override:i amount_expr:?s sort_order:i due_day:?i confirmed_at:?s confirmed_month:?m
        confirmed_cash_flow_id:?i created_at:s updated_at:s"""),
    "cash_flows": _shape("id:i occurred_on:d title:s amount_value:n sort_order:i is_primary_income:i created_at:s updated_at:s"),
    "card_payment_batches": _shape("id:i usage_month:m source:s status:s created_at:s"),
    "card_payment_batch_items": _shape("id:i batch_id:i entry_id:i entry_payment_key:s created_at:s"),
    "card_payment_events": _shape("""id:i batch_id:?i event_date:d event_type:s total_amount:n note:s
        cash_flow_id:?i idempotency_key:?s request_fingerprint:?s created_at:s"""),
    "card_payment_allocations": _shape("id:i payment_event_id:i entry_payment_key:s amount_value:n created_at:s"),
    "card_payment_deferrals": _shape("""entry_payment_key:s from_payment_month:m target_payment_month:m
        original_book_section:?s original_entry_date:?d original_date_label:?s original_group_label:?s
        original_title:?s original_sort_order:?i created_at:s"""),
    "notification_candidate_registrations": _shape("registration_key:s target:s target_id:i request_fingerprint:s created_at:s"),
    "app_settings": _shape("key:s value:s updated_at:s"),
    "app_labels": _shape("key:s value:s updated_at:s"),
}
PRIMARY = {table: ("entry_payment_key" if table == "card_payment_deferrals" else
                   "registration_key" if table == "notification_candidate_registrations" else
                   "key" if table in ("app_settings", "app_labels") else "id") for table in TABLES}


def valid_date(value):
    if type(value) is not str or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def valid_month(value):
    return type(value) is str and valid_date(value + "-01")


def valid_stamp(value):
    if type(value) is not str or not re.fullmatch(
            r"[0-9]{4}-[0-9]{2}-[0-9]{2}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?", value):
        return False
    offset = re.search(r"[+-]([0-9]{2}):([0-9]{2})$", value)
    if offset and (int(offset[1]) > 23 or int(offset[2]) > 59):
        return False
    try:
        datetime.fromisoformat(value)
        return True
    except ValueError:
        return False


def setting_money(value):
    # B-2 string-money grammar, not Decimal's broader underscore/exponent syntax.
    if type(value) is not str or not re.fullmatch(r"[+-]?[0-9]+(?:\.0+)?", value.strip()):
        fail("REJECT_SETTING_MONEY")
    try:
        amount = Decimal(value.strip())
    except (InvalidOperation, AttributeError):
        fail("REJECT_SETTING_MONEY")
    if not amount.is_finite() or amount.copy_abs() > MAX_MONEY or amount != amount.to_integral_value():
        fail("REJECT_SETTING_MONEY")
    return int(amount)


def admit_row(table, row):
    """Validate without coercing any stored class, text, signed zero or NULL."""
    if table not in SHAPES or type(row) is not dict or set(row) != set(SHAPES[table]):
        fail("REJECT_ROW_SHAPE")
    if table == "app_settings" and row.get("key") in SENSITIVE:
        fail("REJECT_SENSITIVE_SETTING")  # before copying/encoding any value
    for name, spec in SHAPES[table].items():
        value = row[name]
        if spec.startswith("?"):
            if value is None:
                continue
            spec = spec[1:]
        if spec == "i":
            integer(value)  # native B-2 int fields, not a money conversion
        elif spec == "n":
            money(value)
        elif type(value) is not str or (spec == "d" and not valid_date(value)) or (
                spec == "m" and not valid_month(value)):
            fail("REJECT_ROW_TYPE")
    if table == "ledger_entries" and row["book_section"] not in ("current", "archive"):
        fail("REJECT_ROW_DOMAIN")
    if table == "card_payment_events" and row["event_type"] not in ("immediate", "discount"):
        fail("REJECT_ROW_DOMAIN")
    if table == "notification_candidate_registrations" and row["target"] not in ("ledger", "claim", "family_card"):
        fail("REJECT_ROW_DOMAIN")
    if table == "card_payment_allocations" and money(row["amount_value"]) < 0:
        fail("REJECT_ROW_DOMAIN")
    if table == "app_settings":
        if row["key"] in MONEY_SETTING_FIELDS:
            setting_money(row["value"])
        if row["key"] == "last_closed_month" and not valid_month(row["value"]):
            fail("REJECT_ROW_DOMAIN")
    return encode(row)  # complete Unicode check, including every key


@dataclass(frozen=True)
class Row:
    table: str
    key: Key
    raw: bytes

    def __post_init__(self):
        value = decode_c1(self.raw)
        admitted = admit_row(self.table, value)
        if self.key != Key(value[PRIMARY[self.table]]) or admitted != self.raw:
            fail("REJECT_ROW_KEY")

    @classmethod
    def make(cls, table, value):
        raw = admit_row(table, value)
        return cls(table, Key(value[PRIMARY[table]]), raw)

    def value(self):
        # Bytes were already strictly admitted at creation. Return a fresh copy.
        from json import loads
        return loads(self.raw)

    def wire(self):
        return dict(key=self.key.wire(), value=self.value())

    def hash(self, context):
        return row_hash(context, self.table, self.key, self.value())
