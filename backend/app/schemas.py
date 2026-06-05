from pydantic import BaseModel, Field, field_validator


def integer_money(value: object) -> object:
    """비율이 아닌 돈은 원 단위 정수로만 받는다."""
    if value is None:
        return value
    amount = float(value)
    if not amount.is_integer():
        raise ValueError("money amount must be an integer")
    return int(amount)


class LoginIn(BaseModel):
    username: str
    password: str


class SharePinIn(BaseModel):
    pin: str = Field(pattern="^[0-9]{4}$")


class AuthUser(BaseModel):
    id: int
    username: str
    display_name: str
    session_token: str | None = None
    share_pin_needs_change: bool = False


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
    payment_key: str | None = None

    _integer_money = field_validator("amount_value", "aux_amount_value", mode="before")(integer_money)

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

    _integer_money = field_validator("amount_value", "aux_amount_value", mode="before")(integer_money)


class MonthCloseIn(BaseModel):
    allow_early_close: bool = False


class PlannedEntryIn(BaseModel):
    title: str
    usage_place: str = Field(min_length=1)
    usage_item: str | None = None
    amount_value: float = Field(ge=0)
    amount_expr: str | None = None
    due_day: int = Field(ge=1, le=31)

    _integer_money = field_validator("amount_value", mode="before")(integer_money)


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
    spent_on: str | None = None
    amount_value: float | None = None
    discount_amount: float = 0
    amount_expr: str | None = None
    sort_order: int
    due_day: int | None = None
    confirmed_at: str | None = None


class MonthlyPanelIn(BaseModel):
    month: str
    panel_type: str
    title: str = ""
    spent_on: str | None = None
    amount_value: float | None = Field(default=None, ge=0)
    discount_amount: float = Field(default=0, ge=0)
    amount_expr: str | None = None
    sort_order: int
    due_day: int | None = None

    _integer_money = field_validator("amount_value", "discount_amount", mode="before")(integer_money)


class MonthlyPanelPatch(BaseModel):
    month: str | None = None
    panel_type: str | None = None
    title: str | None = None
    spent_on: str | None = None
    amount_value: float | None = Field(default=None, ge=0)
    discount_amount: float | None = Field(default=None, ge=0)
    amount_expr: str | None = None
    sort_order: int | None = None
    due_day: int | None = None
    confirmed_at: str | None = None

    _integer_money = field_validator("amount_value", "discount_amount", mode="before")(integer_money)


class SettingPatch(BaseModel):
    value: str


class CsvBackupImportIn(BaseModel):
    filename: str
    content_base64: str


class CashFlow(BaseModel):
    id: int
    occurred_on: str
    title: str
    amount_value: float
    sort_order: int
    is_primary_income: int = 0


class CashFlowIn(BaseModel):
    occurred_on: str
    title: str = ""
    amount_value: float
    sort_order: int
    is_primary_income: int = 0

    _integer_money = field_validator("amount_value", mode="before")(integer_money)


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
    principal_amount: float = Field(ge=0)
    fee_rate: float = Field(default=0, ge=0)
    months: int
    remaining_months: int | None = None
    start_month: str
    sort_order: int

    _integer_money = field_validator("principal_amount", mode="before")(integer_money)


class CardPaymentAllocationIn(BaseModel):
    entry_payment_key: str
    amount_value: float = Field(gt=0)

    _integer_money = field_validator("amount_value", mode="before")(integer_money)


class CardPaymentEventIn(BaseModel):
    event_date: str
    event_type: str = Field(pattern="^(immediate|discount)$")
    note: str = ""
    allocations: list[CardPaymentAllocationIn]


class CardDiscountPolicyPatch(BaseModel):
    policy: str = Field(pattern="^(undecided|enabled|disabled)$")


class PanelDiscountPatch(BaseModel):
    discount_amount: float = Field(ge=0)

    _integer_money = field_validator("discount_amount", mode="before")(integer_money)


class LateCardEntryIn(BaseModel):
    entry_date: str
    usage_place: str | None = None
    usage_item: str | None = None
    amount_value: float = Field(ge=0)

    _integer_money = field_validator("amount_value", mode="before")(integer_money)
