import { API_BASE_URL, authHeaders, getJson, postJson, readDownloadFilename } from "./client";
import { PreRestoreBackup } from "./types";

export async function resetLedgerData(password: string): Promise<{ deleted: Record<string, number> }> {
  return postJson("/api/admin/reset-ledger-data", { password });
}

export async function restoreSnapshot(
  password: string,
  snapshotText: string,
): Promise<{ restored: Record<string, number> }> {
  return postJson("/api/admin/snapshot/restore", { password, snapshot_text: snapshotText });
}

export async function fetchPreRestoreBackups(): Promise<PreRestoreBackup[]> {
  const result = await getJson<{ backups: PreRestoreBackup[] }>("/api/admin/snapshot/pre-restore");
  return result.backups;
}

export async function downloadPreRestoreBackup(filename: string): Promise<{ blob: Blob; filename: string }> {
  const response = await fetch(`${API_BASE_URL}/api/admin/snapshot/pre-restore/${encodeURIComponent(filename)}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `HTTP ${response.status}`);
  }
  return {
    blob: await response.blob(),
    filename: readDownloadFilename(response.headers.get("Content-Disposition")) ?? filename,
  };
}

export async function restorePreRestoreBackup(
  filename: string,
  password: string,
): Promise<{ restored: Record<string, number> }> {
  return postJson(`/api/admin/snapshot/pre-restore/${encodeURIComponent(filename)}/restore`, { password });
}
