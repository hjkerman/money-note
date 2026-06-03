const SESSION_TOKEN_KEY = "money-note-session-token";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl();

export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
  session_token?: string | null;
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
};

export type SpendingCategory = "essential" | "questionable";

export type MonthlyPanel = {
  id: number;
  month: string;
  panel_type: "fixed" | "frozen" | "claim" | "settlement";
  title: string;
  amount_value: number | null;
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

export async function createEntry(payload: Omit<LedgerEntry, "id">): Promise<LedgerEntry> {
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

export async function deletePanelsByType(panelType: MonthlyPanel["panel_type"]): Promise<{ deleted: number }> {
  return deleteJson(`/api/month/current/panels/type/${panelType}`);
}

export async function confirmPlannedEntry(entryId: number): Promise<{ planned: LedgerEntry; entry: LedgerEntry }> {
  return postJson(`/api/month/current/planned/${entryId}/confirm`, {});
}

export async function confirmFrozenPanel(panelId: number): Promise<{ entry: LedgerEntry }> {
  return postJson(`/api/month/current/panels/${panelId}/confirm-frozen`, {});
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

export async function closeCurrentMonth(): Promise<{ archived: number; deleted_from_current: number }> {
  return postJson("/api/month/current/close", {});
}

export async function createExport(): Promise<{ filename: string; latest: string }> {
  return postJson("/api/export", {});
}

export function latestExportUrl(): string {
  return `${API_BASE_URL}/api/export/latest.xlsx`;
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
