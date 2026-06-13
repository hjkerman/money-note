export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
  session_token?: string | null;
  share_pin_needs_change: boolean;
};

export type LedgerEntry = {
  id: number;
  book_section: "current" | "archive";
  entry_kind: string;
  entry_date: string | null;
  date_label: string | null;
  group_label: string | null;
  title: string;
  usage_place: string | null;
  usage_item: string | null;
  amount_value: number | null;
  amount_expr: string | null;
  aux_amount_value: number | null;
  aux_amount_expr: string | null;
  extra_value: string | null;
  sort_order: number;
  due_day: number | null;
  confirmed_at: string | null;
  spending_category: SpendingCategory | null;
  payment_key: string | null;
  discount_override: number;
};

export type SpendingCategory = "essential" | "questionable" | "dignity";

export type JudgmentTone = {
  level: "quiet" | "steady" | "warning" | "danger";
  message: string;
};

export type JudgmentStatTone = {
  key: SpendingCategory | null;
  title: string;
  caption: string;
};

export type JudgmentState = {
  category_labels: Record<SpendingCategory | "unclassified", string>;
  stat_tones: JudgmentStatTone[];
  claim_categories: Record<string, SpendingCategory | null>;
  budget: JudgmentTone;
  credit: JudgmentTone;
  payment: JudgmentTone;
};

export type MonthlyPanel = {
  id: number;
  month: string;
  panel_type: "fixed" | "frozen" | "claim" | "family_card";
  title: string;
  spent_on: string | null;
  amount_value: number | null;
  discount_amount: number;
  discount_override: number;
  amount_expr: string | null;
  sort_order: number;
  due_day: number | null;
  confirmed_at: string | null;
};

export type Summary = {
  base_next_month_liquidity: number;
  card_total: number;
  planned_recurring_total: number;
  transfer_or_deposit_total: number;
  interest_expense: number;
  frozen_asset_total: number;
  liquidity_status: number;
  next_month_liquidity: number;
};

export type CashFlow = {
  id: number;
  occurred_on: string;
  title: string;
  amount_value: number;
  sort_order: number;
  is_primary_income: number;
};

export type CardPaymentRow = LedgerEntry & {
  original_amount: number;
  immediate_paid_amount: number;
  discount_amount: number;
  remaining_amount: number;
  is_transport: boolean;
  is_toll: boolean;
  is_deferred: boolean;
  is_carried_over: boolean;
  is_group: boolean;
  payment_keys: string[];
  entry_ids: number[];
  payment_parts: { entry_payment_key: string; entry_id: number; remaining_amount: number }[];
};

export type CardPaymentEvent = {
  id: number;
  event_date: string;
  event_type: "immediate" | "discount";
  total_amount: number;
  note: string;
  cash_flow_id: number | null;
};

export type CardPaymentStatus = {
  payment_month: string;
  usage_month: string;
  due_date: string;
  immediate_allowed: boolean;
  needs_liquidity_reset: boolean;
  liquidity_reset_acknowledged: boolean;
  original_total: number;
  immediate_paid_total: number;
  discount_total: number;
  recorded_remaining_total: number;
  effective_remaining_total: number;
  primary_income_total: number;
  discount_policy: CardDiscountPolicy;
  rows: CardPaymentRow[];
  events: CardPaymentEvent[];
};

export type CardDiscountPolicy = "enabled" | "disabled";

export type CardDiscountMonth = {
  month: string;
  scope: "owner" | "family";
  policy: CardDiscountPolicy;
  discounts: Record<string, number>;
  discount_total: number;
};

export type MonthCloseStatus = {
  calendar_date: string;
  calendar_month: string;
  oldest_open_month: string | null;
  last_closed_month: string | null;
  needs_close: boolean;
  is_early_close: boolean;
  early_close_available: boolean;
  early_close_start_day: number;
  can_close: boolean;
};

export type AuditLog = {
  id: number;
  occurred_at: string;
  actor_username: string;
  method: string;
  path: string;
  status_code: number;
};

export type PreRestoreBackup = {
  filename: string;
  created_at: string;
  size_bytes: number;
  snapshot_id: string;
  exported_at: string | null;
};

export type Labels = Record<string, string>;
export type Settings = Record<string, string>;
