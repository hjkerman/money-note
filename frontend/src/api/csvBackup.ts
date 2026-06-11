import { API_BASE_URL, authHeaders, fileToBase64, postJson, readableErrorMessage, readDownloadFilename } from "./client";

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
