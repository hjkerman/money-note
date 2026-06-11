import { postJson } from "./client";

export async function resetLedgerData(password: string): Promise<{ deleted: Record<string, number> }> {
  return postJson("/api/admin/reset-ledger-data", { password });
}

export async function restoreSnapshot(
  password: string,
  snapshot: unknown,
): Promise<{ restored: Record<string, number> }> {
  return postJson("/api/admin/snapshot/restore", { password, snapshot });
}
