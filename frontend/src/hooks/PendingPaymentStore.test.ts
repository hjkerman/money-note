import { expect, it } from "vitest";
import { PendingPaymentStore } from "./PendingPaymentStore";

it("keeps the v1 user-scoped JSON and retry identity across read/write", () => {
  const values = new Map<string, string>();
  const store = new PendingPaymentStore(() => ({
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  }), () => "stable-key-00000001");
  const payload = { event_date: "2026-09-17", event_type: "immediate" as const, note: "", allocations: [{ entry_payment_key: "p1", amount_value: 500 }] };
  const pending = store.create(payload, { p1: "500" });
  store.save(7, pending);
  expect(values.get("money-note-pending-card-payment-v1:7")).toBe(JSON.stringify({
    fingerprint: JSON.stringify(payload), key: "stable-key-00000001", payload, draftAllocations: { p1: "500" },
  }));
  expect(store.read(7)).toEqual(pending);
  expect(store.read(8)).toBeNull();
  store.clear(7);
  expect(store.read(7)).toBeNull();
});

it("fails closed on malformed or mismatched persisted retry requests", () => {
  const values = new Map<string, string>();
  const store = new PendingPaymentStore(() => ({
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => { values.set(key, value); },
    removeItem: (key) => { values.delete(key); },
  }));
  const key = PendingPaymentStore.storageKey(7);
  for (const raw of ["{", "null", "{}", JSON.stringify({
    key: "stable-key-00000001", fingerprint: "different", payload: { event_type: "immediate" }, draftAllocations: {},
  })]) {
    values.set(key, raw);
    expect(store.read(7)).toBe("corrupt");
    expect(values.get(key)).toBe(raw);
  }
});
