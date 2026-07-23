import { API_BASE_URL, deleteJson, getJson, patchJson, postJson } from "./client";
import { MonthlyPanel } from "./types";

type MonthlyPanelWrite = Omit<
  MonthlyPanel,
  | "id"
  | "discount_policy"
  | "automatic_discount_eligible"
  | "automatic_discount_amount"
  | "effective_discount_amount"
  | "effective_amount_value"
>;

export function sharePageUrl(panelType: "claim" | "family_card"): string {
  const baseUrl = API_BASE_URL || (typeof window === "undefined" ? "" : window.location.origin);
  return new URL(`/share/${panelType}`, baseUrl).toString();
}

export async function fetchCurrentPanels(): Promise<MonthlyPanel[]> {
  return getJson("/api/month/current/panels");
}

export async function createPanel(payload: MonthlyPanelWrite): Promise<MonthlyPanel> {
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
