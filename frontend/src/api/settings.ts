import { deleteJson, getJson, patchJson, postJson } from "./client";
import { AuditLog, CashFlow, JudgmentState, Labels, Settings, Summary } from "./types";

export async function fetchSummary(): Promise<Summary> {
  return getJson("/api/month/current/summary");
}

export async function fetchJudgment(): Promise<JudgmentState> {
  return getJson("/api/judgment/current");
}

export async function fetchCashFlows(
  query: { dateFrom?: string; dateTo?: string; limit?: number } = {},
): Promise<CashFlow[]> {
  const params = new URLSearchParams();
  if (query.dateFrom) params.set("from", query.dateFrom);
  if (query.dateTo) params.set("to", query.dateTo);
  if (query.limit !== undefined) params.set("limit", String(query.limit));
  const queryString = params.toString();
  return getJson(`/api/cash-flows${queryString ? `?${queryString}` : ""}`);
}

export async function createCashFlow(payload: Omit<CashFlow, "id">): Promise<CashFlow> {
  return postJson("/api/cash-flows", payload);
}

export async function deleteCashFlow(flowId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/cash-flows/${flowId}`);
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

export async function fetchAuditLogs(): Promise<AuditLog[]> {
  return getJson("/api/audit-logs");
}

export async function clearAuditLogs(): Promise<{ deleted: number }> {
  return deleteJson("/api/audit-logs");
}

export async function closeCurrentMonth(allowEarlyClose = false): Promise<{
  closed_month: string | null;
  archived: number;
  deleted_from_current: number;
}> {
  return postJson("/api/month/current/close", { allow_early_close: allowEarlyClose });
}
