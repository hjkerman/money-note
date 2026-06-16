import { deleteJson, getJson, patchJson, postJson } from "./client";
import { LedgerEntry } from "./types";

export async function fetchCurrentEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/entries/current");
}

export async function fetchArchiveEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/entries/archive");
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

export async function fetchConfirmedPlannedEntries(): Promise<LedgerEntry[]> {
  return getJson("/api/month/current/planned/confirmed");
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

export async function confirmPlannedEntry(
  entryId: number,
  payload: { entry_date?: string | null } = {},
): Promise<{ planned: LedgerEntry; entry: LedgerEntry }> {
  return postJson(`/api/month/current/planned/${entryId}/confirm`, payload);
}
