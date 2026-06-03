const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:18080";

export type AuthUser = {
  id: number;
  username: string;
  display_name: string;
};

export type LedgerEntry = {
  id: number;
  book_section: "current" | "archive";
  entry_kind: string;
  entry_date: string | null;
  date_label: string | null;
  group_label: string | null;
  title: string;
  amount_value: number | null;
  amount_expr: string | null;
  aux_amount_value: number | null;
  aux_amount_expr: string | null;
  extra_value: string | null;
  sort_order: number;
  due_day: number | null;
  confirmed_at: string | null;
};

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

export type Labels = Record<string, string>;

export async function fetchMe(): Promise<AuthUser> {
  return getJson("/api/auth/me");
}

export async function login(payload: { username: string; password: string }): Promise<AuthUser> {
  return postJson("/api/auth/login", payload);
}

export async function logout(): Promise<{ ok: boolean }> {
  return postJson("/api/auth/logout", {});
}

export async function fetchCurrentEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/entries/current");
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

export async function fetchLabels(): Promise<Labels> {
  return getJson("/api/labels");
}

export async function appendPlannedEntry(payload: {
  title: string;
  amount_value: number | null;
  due_day: number | null;
}): Promise<LedgerEntry> {
  return postJson("/api/month/current/planned", payload);
}

export async function createEntry(payload: Omit<LedgerEntry, "id">): Promise<LedgerEntry> {
  return postJson("/api/entries", payload);
}

export async function createPanel(payload: Omit<MonthlyPanel, "id">): Promise<MonthlyPanel> {
  return postJson("/api/month/current/panels", payload);
}

export async function confirmPlannedEntry(entryId: number): Promise<{ planned: LedgerEntry; entry: LedgerEntry }> {
  return postJson(`/api/month/current/planned/${entryId}/confirm`, {});
}

export async function createCashFlow(payload: Omit<CashFlow, "id">): Promise<CashFlow> {
  return postJson("/api/cash-flows", payload);
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
    credentials: "include",
  });
  return parseResponse(response);
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    credentials: "include",
  });
  return parseResponse(response);
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}
