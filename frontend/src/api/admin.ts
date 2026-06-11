import { postJson } from "./client";

export async function resetLedgerData(password: string): Promise<{ deleted: Record<string, number> }> {
  return postJson("/api/admin/reset-ledger-data", { password });
}
