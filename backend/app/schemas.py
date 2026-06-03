from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    id: int
    username: str
    display_name: str
    session_token: str | None = None


class LedgerEntryIn(BaseModel):
    book_section: str = Field(pattern="^(current|archive)$")
    entry_kind: str = "expense"
    entry_date: str | None = None
    date_label: str | None = None
    group_label: str | None = None
    title: str = ""
    usage_place: str | None = None
    usage_item: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    aux_amount_value: float | None = None
    aux_amount_expr: str | None = None
    extra_value: str | None = None
    sort_order: int
    due_day: int | None = None
    confirmed_at: str | None = None
    spending_category: str | None = None


class LedgerEntry(LedgerEntryIn):
    id: int


class LedgerEntryPatch(BaseModel):
    entry_kind: str | None = None
    entry_date: str | None = None
    date_label: str | None = None
    group_label: str | None = None
    title: str | None = None
    usage_place: str | None = None
    usage_item: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    aux_amount_value: float | None = None
    aux_amount_expr: str | None = None
    extra_value: str | None = None
    sort_order: int | None = None
    due_day: int | None = None
    confirmed_at: str | None = None
    spending_category: str | None = None


class PlannedEntryIn(BaseModel):
    title: str
    usage_place: str | None = None
    usage_item: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    due_day: int | None = None


class EntryReorder(BaseModel):
    ordered_ids: list[int]


class Summary(BaseModel):
    base_next_month_liquidity: float
    card_total: float
    installment_monthly_total: float
    transfer_or_deposit_total: float
    interest_expense: float
    frozen_asset_total: float
    liquidity_status: float
    next_month_liquidity: float


class MonthlyPanel(BaseModel):
    id: int
    month: str
    panel_type: str
    title: str
    amount_value: float | None = None
    amount_expr: str | None = None
    sort_order: int
    due_day: int | None = None
    confirmed_at: str | None = None


class MonthlyPanelIn(BaseModel):
    month: str
    panel_type: str
    title: str = ""
    amount_value: float | None = None
    amount_expr: str | None = None
    sort_order: int
    due_day: int | None = None


class MonthlyPanelPatch(BaseModel):
    month: str | None = None
    panel_type: str | None = None
    title: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    sort_order: int | None = None
    due_day: int | None = None
    confirmed_at: str | None = None


class SettingPatch(BaseModel):
    value: str


class CashFlow(BaseModel):
    id: int
    occurred_on: str
    title: str
    amount_value: float
    sort_order: int


class CashFlowIn(BaseModel):
    occurred_on: str
    title: str = ""
    amount_value: float
    sort_order: int


class Installment(BaseModel):
    id: int
    title: str
    principal_amount: float
    fee_rate: float
    fee_amount: float
    months: int
    remaining_months: int
    start_month: str
    sort_order: int
    is_active: int
    monthly_amount: float


class InstallmentIn(BaseModel):
    title: str
    principal_amount: float
    fee_rate: float = 0
    months: int
    remaining_months: int | None = None
    start_month: str
    sort_order: int
