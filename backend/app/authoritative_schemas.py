"""Versioned transport projections, not a new Snapshot or replay format.

Every section is required. Opaque existing policy parameters and raw Snapshot
rows retain their existing representations; no client defaults repair gaps.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import CashFlow, LedgerEntry, MonthlyPanel, Summary


class BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BundlePrincipal(BundleModel):
    user_id: int


class DiscountPolicyDefaults(BundleModel):
    owner: Literal["enabled", "disabled"]
    family: Literal["enabled", "disabled"]


class BundleAuthority(BundleModel):
    state_revision: int = Field(ge=0)
    state_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluation_date: str
    discount_policy_defaults: DiscountPolicyDefaults


class RecurringCloseItem(BundleModel):
    kind: Literal["fixed"]
    id: int
    title: str
    amount_value: int | None


class PlannedCloseItem(BundleModel):
    kind: Literal["planned"]
    id: int
    title: str
    detail: str
    amount_value: int
    due_day: int | None


class MonthCloseStatus(BundleModel):
    calendar_date: str
    calendar_month: str
    oldest_open_month: str | None
    last_closed_month: str | None
    needs_close: bool
    is_early_close: bool
    early_close_available: bool
    early_close_start_day: int
    card_recurring_confirmation_available: bool
    can_close: bool
    unconfirmed_recurring_items: list[RecurringCloseItem | PlannedCloseItem]


class PaymentPart(BundleModel):
    entry_payment_key: str
    entry_id: int
    remaining_amount: int


class PaymentRow(BundleModel):
    # Payment rows intentionally retain raw ledger/source/timestamp fields,
    # unlike the narrower LedgerEntry presentation response.
    id: int
    book_section: str
    entry_kind: str
    entry_date: str | None
    date_label: str | None
    group_label: str | None
    title: str
    usage_place: str | None
    usage_item: str | None
    amount_value: int | float | None
    amount_expr: str | None
    aux_amount_value: int | float | None
    aux_amount_expr: str | None
    extra_value: str | None
    sort_order: int
    due_day: int | None
    confirmed_at: str | None
    confirmed_month: str | None
    source_planned_entry_id: int | None
    spending_category: str | None
    payment_key: str | None
    discount_override: int
    created_at: str
    updated_at: str
    original_amount: int
    immediate_paid_amount: int
    discount_amount: int
    discount_policy: str
    automatic_discount_eligible: bool
    automatic_discount_amount: int
    effective_discount_amount: int
    effective_amount_value: int
    remaining_amount: int
    is_transport: bool
    is_toll: bool
    is_deferred: bool
    is_carried_over: bool
    payment_keys: list[str]
    entry_ids: list[int]
    payment_parts: list[PaymentPart]
    is_group: bool


class PaymentEvent(BundleModel):
    id: int
    batch_id: int | None
    event_date: str
    event_type: str
    total_amount: int | float
    note: str | None
    cash_flow_id: int | None
    idempotency_key: str | None
    request_fingerprint: str | None
    created_at: str


class PaymentStatus(BundleModel):
    calendar_date: str
    payment_month: str
    usage_month: str
    due_date: str
    immediate_allowed: bool
    needs_liquidity_reset: bool
    liquidity_reset_acknowledged: bool
    original_total: int
    immediate_paid_total: int
    discount_total: int
    recorded_remaining_total: int
    effective_remaining_total: int
    primary_income_total: int
    discount_policy: str
    rows: list[PaymentRow]
    events: list[PaymentEvent]


class ProjectionPolicy(BundleModel):
    schema_version: int
    policy_id: str
    type: str
    parameters: dict[str, Any]
    rounding: str


class DiscountMonth(BundleModel):
    month: str
    scope: str
    policy: str
    projection_policy: ProjectionPolicy
    discounts: dict[str, int]
    discount_total: int


class TransitProfile(BundleModel):
    card: str
    month: str
    profile: str


class JudgmentMessage(BundleModel):
    level: str
    message: str


class StatTone(BundleModel):
    key: str | None
    title: str
    caption: str


class Judgment(BundleModel):
    category_labels: dict[str, str]
    stat_tones: list[StatTone]
    claim_categories: dict[str, str]
    budget: JudgmentMessage
    credit: JudgmentMessage
    payment: JudgmentMessage


class AuthoritativeProjections(BundleModel):
    month_close_status: MonthCloseStatus
    entries: list[LedgerEntry]
    panels: list[MonthlyPanel]
    summary: Summary
    card_payment_status: PaymentStatus
    judgment: Judgment
    confirmed_planned_entries: list[LedgerEntry]
    cash_flows: list[CashFlow]
    settings: dict[str, str]
    owner_discount_month: DiscountMonth
    family_discount_month: DiscountMonth
    transit_discount_profile: TransitProfile


class AuthoritativeState(BundleModel):
    bundle_version: Literal[1]
    principal: BundlePrincipal
    authority: BundleAuthority
    snapshot: dict[str, Any]
    state: AuthoritativeProjections
