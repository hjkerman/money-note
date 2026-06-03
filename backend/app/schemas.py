from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str
    password: str


class AuthUser(BaseModel):
    id: int
    username: str
    display_name: str


class LedgerEntryIn(BaseModel):
    book_section: str = Field(pattern="^(current|archive)$")
    entry_kind: str = "expense"
    entry_date: str | None = None
    date_label: str | None = None
    group_label: str | None = None
    title: str = ""
    amount_value: float | None = None
    amount_expr: str | None = None
    aux_amount_value: float | None = None
    aux_amount_expr: str | None = None
    extra_value: str | None = None
    sort_order: int


class LedgerEntry(LedgerEntryIn):
    id: int


class LedgerEntryPatch(BaseModel):
    entry_kind: str | None = None
    entry_date: str | None = None
    date_label: str | None = None
    group_label: str | None = None
    title: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    aux_amount_value: float | None = None
    aux_amount_expr: str | None = None
    extra_value: str | None = None
    sort_order: int | None = None


class PlannedEntryIn(BaseModel):
    title: str
    amount_value: float | None = None
    amount_expr: str | None = None


class EntryReorder(BaseModel):
    ordered_ids: list[int]


class Summary(BaseModel):
    base_next_month_liquidity: float
    card_total: float
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


class MonthlyPanelIn(BaseModel):
    month: str
    panel_type: str
    title: str = ""
    amount_value: float | None = None
    amount_expr: str | None = None
    sort_order: int


class MonthlyPanelPatch(BaseModel):
    month: str | None = None
    panel_type: str | None = None
    title: str | None = None
    amount_value: float | None = None
    amount_expr: str | None = None
    sort_order: int | None = None


class SettingPatch(BaseModel):
    value: str
