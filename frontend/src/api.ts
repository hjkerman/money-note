const SESSION_TOKEN_KEY = "money-note-session-token";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl();

export function sharePageUrl(panelType: "claim" | "family_card"): string {
  return `${API_BASE_URL}/share/${panelType}`;
}

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
  installment_monthly_total: number;
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

export type Installment = {
  id: number;
  title: string;
  principal_amount: number;
  fee_rate: number;
  fee_amount: number;
  months: number;
  remaining_months: number;
  start_month: string;
  sort_order: number;
  is_active: number;
  monthly_amount: number;
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

export type CardDiscountPolicy = "undecided" | "enabled" | "disabled";

export type CardDiscountMonth = {
  month: string;
  scope: "owner" | "family";
  policy: CardDiscountPolicy;
  discounts: Record<string, number>;
  discount_total: number;
};

export type MonthCloseStatus = {
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

export type Labels = Record<string, string>;
export type Settings = Record<string, string>;

export async function fetchMe(): Promise<AuthUser> {
  return getJson("/api/auth/me");
}

export async function login(payload: { username: string; password: string }): Promise<AuthUser> {
  const user = await postJson<AuthUser>("/api/auth/login", payload);
  if (user.session_token) {
    localStorage.setItem(SESSION_TOKEN_KEY, user.session_token);
  }
  return user;
}

export async function logout(): Promise<{ ok: boolean }> {
  try {
    return await postJson("/api/auth/logout", {});
  } finally {
    localStorage.removeItem(SESSION_TOKEN_KEY);
  }
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<{ changed: boolean }> {
  return patchJson("/api/auth/password", payload);
}

export async function resetLedgerData(password: string): Promise<{ deleted: Record<string, number> }> {
  return postJson("/api/admin/reset-ledger-data", { password });
}

export async function fetchCurrentEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/entries/current");
}

export async function fetchArchiveEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/entries/archive");
}

export async function fetchCurrentPanels(): Promise<MonthlyPanel[]> {
  return getJson("/api/month/current/panels");
}

export async function fetchSummary(): Promise<Summary> {
  return getJson("/api/month/current/summary");
}

export async function fetchJudgment(): Promise<JudgmentState> {
  return getJson("/api/judgment/current");
}

export async function fetchCashFlows(): Promise<CashFlow[]> {
  return getJson("/api/cash-flows");
}

export async function fetchInstallments(): Promise<Installment[]> {
  return getJson("/api/installments");
}

export async function fetchLabels(): Promise<Labels> {
  return getJson("/api/labels");
}

export async function fetchSettings(): Promise<Settings> {
  return getJson("/api/settings");
}

export async function updateSetting(key: string, value: string): Promise<Record<string, string>> {
  return patchJson(`/api/settings/${key}`, { value });
}

export async function setSharePin(pin: string): Promise<{ configured: boolean; needs_change: boolean }> {
  return postJson("/api/share/pin", { pin });
}

export async function fetchCurrentCardPayments(): Promise<CardPaymentStatus> {
  return getJson("/api/card-payments/current");
}

export async function fetchCardDiscountMonth(
  month: string,
  scope: "owner" | "family",
): Promise<CardDiscountMonth> {
  return getJson(`/api/card-discounts/months/${month}?scope=${scope}`);
}

export async function updateCardDiscountPolicy(
  month: string,
  scope: "owner" | "family",
  policy: CardDiscountPolicy,
): Promise<CardDiscountMonth> {
  return patchJson(`/api/card-discounts/months/${month}?scope=${scope}`, { policy });
}

export async function updateEntryDiscount(entryPaymentKey: string, discountAmount: number): Promise<LedgerEntry> {
  return patchJson(`/api/card-discounts/entries/${entryPaymentKey}`, { discount_amount: discountAmount });
}

export async function clearEntryDiscount(entryPaymentKey: string): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-discounts/entries/${entryPaymentKey}`);
}

export async function fetchMonthCloseStatus(): Promise<MonthCloseStatus> {
  return getJson("/api/month/current/status");
}

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return getJson("/api/audit-logs");
}

export async function clearAuditLogs(): Promise<{ deleted: number }> {
  return deleteJson("/api/audit-logs");
}

export async function createCardPaymentEvent(payload: {
  event_date: string;
  event_type: "immediate" | "discount";
  note: string;
  allocations: { entry_payment_key: string; amount_value: number }[];
}): Promise<CardPaymentEvent> {
  return postJson("/api/card-payments/events", payload);
}

export async function deleteCardPaymentEvent(eventId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-payments/events/${eventId}`);
}

export async function acknowledgeLiquidityReset(): Promise<{ payment_month: string }> {
  return postJson("/api/card-payments/acknowledge-liquidity-reset", {});
}

export async function deferTollPayment(entryPaymentKey: string): Promise<{
  entry_payment_key: string;
  from_payment_month: string;
  target_payment_month: string;
}> {
  return postJson(`/api/card-payments/deferrals/${entryPaymentKey}`, {});
}

export async function cancelTollDeferral(entryPaymentKey: string): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-payments/deferrals/${entryPaymentKey}`);
}

export async function createLateCardEntry(payload: {
  entry_date: string;
  usage_place: string | null;
  usage_item: string | null;
  amount_value: number;
}): Promise<LedgerEntry> {
  return postJson("/api/card-payments/late-entries", payload);
}

export async function appendPlannedEntry(payload: {
  title: string;
  usage_place: string | null;
  usage_item: string | null;
  amount_value: number | null;
  due_day: number | null;
}): Promise<LedgerEntry> {
  return postJson("/api/month/current/planned", payload);
}

export async function deletePlannedEntry(entryId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/month/current/planned/${entryId}`);
}

export async function createEntry(payload: Omit<LedgerEntry, "id" | "payment_key">): Promise<LedgerEntry> {
  return postJson("/api/entries", payload);
}

export async function updateEntry(entryId: number, payload: Partial<Omit<LedgerEntry, "id">>): Promise<LedgerEntry> {
  return patchJson(`/api/entries/${entryId}`, payload);
}

export async function deleteEntry(entryId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/entries/${entryId}`);
}

export async function createPanel(payload: Omit<MonthlyPanel, "id">): Promise<MonthlyPanel> {
  return postJson("/api/month/current/panels", payload);
}

export async function deletePanel(panelId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/month/current/panels/${panelId}`);
}

export async function updatePanelDiscount(panelId: number, discountAmount: number): Promise<MonthlyPanel> {
  return patchJson(`/api/month/current/panels/${panelId}/discount`, { discount_amount: discountAmount });
}

export async function clearPanelDiscount(panelId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/month/current/panels/${panelId}/discount`);
}

export async function deletePanelsByType(panelType: MonthlyPanel["panel_type"]): Promise<{ deleted: number }> {
  return deleteJson(`/api/month/current/panels/type/${panelType}`);
}

export async function completePanelsByType(panelType: "claim" | "family_card"): Promise<{ completed: number }> {
  return postJson(`/api/month/current/panels/type/${panelType}/complete`, {});
}

export async function confirmPlannedEntry(entryId: number): Promise<{ planned: LedgerEntry; entry: LedgerEntry }> {
  return postJson(`/api/month/current/planned/${entryId}/confirm`, {});
}

export async function createCashFlow(payload: Omit<CashFlow, "id">): Promise<CashFlow> {
  return postJson("/api/cash-flows", payload);
}

export async function createInstallment(payload: Omit<Installment, "id" | "is_active" | "monthly_amount" | "fee_amount">): Promise<Installment> {
  return postJson("/api/installments", payload);
}

export async function deleteInstallment(installmentId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/installments/${installmentId}`);
}

export async function deleteCashFlow(flowId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/cash-flows/${flowId}`);
}

export async function closeCurrentMonth(allowEarlyClose = false): Promise<{
  closed_month: string | null;
  archived: number;
  deleted_from_current: number;
}> {
  return postJson("/api/month/current/close", { allow_early_close: allowEarlyClose });
}

export async function downloadCsvBackup(): Promise<{ filename: string; blob: Blob }> {
  const response = await fetch(`${API_BASE_URL}/api/backups/csv`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(readableErrorMessage(response.status, detail));
  }
  const filename = readDownloadFilename(response.headers.get("Content-Disposition"))
    ?? `money-note-data-dump-${new Date().toISOString().slice(0, 10)}.csv`;
  return { filename, blob: await response.blob() };
}

export async function importCsvBackup(file: File): Promise<{ filename: string; imported: Record<string, number> }> {
  const contentBase64 = await fileToBase64(file);
  return postJson("/api/backups/csv/import", {
    filename: file.name,
    content_base64: contentBase64,
  });
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return parseResponse(response);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return parseResponse(response);
}

function defaultApiBaseUrl(): string {
  if (typeof window === "undefined") return "http://127.0.0.1:18080";
  const { protocol, hostname } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${protocol}//${hostname}:18080`;
  }
  return "http://127.0.0.1:18080";
}

function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(SESSION_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function readDownloadFilename(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename="([^"]+)"/);
  return match?.[1] ?? null;
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const result = String(reader.result ?? "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    });
    reader.addEventListener("error", () => reject(reader.error ?? new Error("파일을 읽지 못했습니다.")));
    reader.readAsDataURL(file);
  });
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(readableErrorMessage(response.status, detail));
  }
  return response.json() as Promise<T>;
}

function readableErrorMessage(status: number, detail: string): string {
  const parsedDetail = parseErrorDetail(detail);
  if (status === 401 && parsedDetail === "invalid username or password") {
    return "아이디 또는 비밀번호가 맞지 않습니다.";
  }
  if (status === 401 && parsedDetail === "authentication required") {
    return "authentication required";
  }
  return parsedDetail || `HTTP ${status}`;
}

function parseErrorDetail(detail: string): string {
  if (!detail) return "";
  try {
    const parsed = JSON.parse(detail) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    return detail;
  }
  return detail;
}
