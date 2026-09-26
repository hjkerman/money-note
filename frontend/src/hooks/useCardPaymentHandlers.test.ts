import { createElement } from "react";
import { renderToString } from "react-dom/server";
import { afterEach, expect, it, vi } from "vitest";
import type { CardPaymentStatus } from "../api";
import { ApiResponseError } from "../api/client";
import { useCardPaymentHandlers } from "./useCardPaymentHandlers";

const api = vi.hoisted(() => ({ createCardPaymentEvent: vi.fn() }));
vi.mock("../api", () => ({ createCardPaymentEvent: api.createCardPaymentEvent }));

afterEach(() => {
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

it("retains the immediate-payment retry key and draft after a lost response", async () => {
  let nextKey = 0;
  vi.stubGlobal("window", { confirm: () => true });
  vi.stubGlobal("crypto", { randomUUID: () => `retry-key-${++nextKey}-00000000` });
  const storage = new Map<string, string>();
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  api.createCardPaymentEvent.mockRejectedValueOnce(new Error("response lost")).mockResolvedValueOnce({});
  const statuses: string[] = [];
  const setPaymentAllocations = vi.fn();
  let handlers: ReturnType<typeof useCardPaymentHandlers> | undefined;
  const cardPayments = {
    immediate_allowed: true,
    calendar_date: "2026-09-17",
    rows: [{ payment_key: "payment-1", payment_parts: [{ entry_payment_key: "payment-1", entry_id: 1, remaining_amount: 500 }] }],
  } as CardPaymentStatus;

  function Probe() {
    handlers = useCardPaymentHandlers({
      cardPayments,
      lateEntryForm: { date: "", usagePlace: "", usageItem: "", amount: "" },
      paymentAllocations: { "payment-1": "500" },
      paymentBudget: "",
      setLateEntryForm: vi.fn(),
      setPaymentAllocations,
      setStatus: (value) => statuses.push(value),
      summary: null,
      userId: 1,
      withRefresh: async (action) => {
        try {
          await action();
          return true;
        } catch {
          return false;
        }
      },
    });
    return null;
  }
  renderToString(createElement(Probe));
  await handlers!.handleCardPaymentSubmit();
  expect(statuses).not.toContain("즉시결제 반영 완료");
  expect(setPaymentAllocations).not.toHaveBeenCalled();
  expect(storage.size).toBe(1);

  await handlers!.handleCardPaymentSubmit();
  expect(api.createCardPaymentEvent).toHaveBeenCalledTimes(2);
  expect(api.createCardPaymentEvent.mock.calls[1][0].idempotency_key).toBe(
    api.createCardPaymentEvent.mock.calls[0][0].idempotency_key,
  );
  expect(storage.size).toBe(0);
  const clearSubmitted = setPaymentAllocations.mock.calls[0][0] as (current: Record<string, string>) => Record<string, string>;
  expect(clearSubmitted({ "payment-1": "500" })).toEqual({});
  expect(clearSubmitted({ "payment-1": "300" })).toEqual({ "payment-1": "300" });
});

it("recovers an ambiguous immediate payment after a page restart using its original payload", async () => {
  const storage = new Map<string, string>();
  vi.stubGlobal("window", { confirm: () => true });
  vi.stubGlobal("crypto", { randomUUID: () => "fixed-payment-retry-key-0001" });
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  api.createCardPaymentEvent.mockRejectedValueOnce(new Error("response lost")).mockResolvedValueOnce({});
  const cardPayments = {
    immediate_allowed: true,
    calendar_date: "2026-09-17",
    rows: [{ payment_key: "payment-1", payment_parts: [{ entry_payment_key: "payment-1", entry_id: 1, remaining_amount: 500 }] }],
  } as CardPaymentStatus;
  let handlers: ReturnType<typeof useCardPaymentHandlers> | undefined;
  let allocations = { "payment-1": "500" };
  const statuses: string[] = [];
  const setPaymentAllocations = vi.fn();
  function Probe() {
    handlers = useCardPaymentHandlers({
      cardPayments,
      lateEntryForm: { date: "", usagePlace: "", usageItem: "", amount: "" },
      paymentAllocations: allocations,
      paymentBudget: "",
      setLateEntryForm: vi.fn(),
      setPaymentAllocations,
      setStatus: (value) => statuses.push(value),
      summary: null,
      userId: 1,
      withRefresh: async (action) => {
        try {
          await action();
          return true;
        } catch {
          return false;
        }
      },
    });
    return null;
  }
  renderToString(createElement(Probe));
  await handlers!.handleCardPaymentSubmit();
  expect(storage.size).toBe(1);

  allocations = { "payment-1": "300" }; // A new draft cannot replace the ambiguous request.
  renderToString(createElement(Probe));
  expect(handlers!.hasPendingPayment).toBe(true);
  await handlers!.handleCardPaymentSubmit();
  expect(api.createCardPaymentEvent).toHaveBeenCalledTimes(1);
  expect(statuses.at(-1)).toContain("이전 미확정 즉시결제");
  await handlers!.confirmPendingPayment();
  expect(api.createCardPaymentEvent).toHaveBeenCalledTimes(2);
  expect(api.createCardPaymentEvent.mock.calls[1][0]).toEqual(api.createCardPaymentEvent.mock.calls[0][0]);
  expect(storage.size).toBe(0);
  const clearSubmitted = setPaymentAllocations.mock.calls[0][0] as (current: Record<string, string>) => Record<string, string>;
  expect(clearSubmitted({ "payment-1": "300" })).toEqual({ "payment-1": "300" });
});

it("does not send a payment when durable retry storage is unavailable", async () => {
  vi.stubGlobal("window", { confirm: () => true });
  vi.stubGlobal("crypto", { randomUUID: () => "fixed-payment-retry-key-0002" });
  vi.stubGlobal("localStorage", {
    getItem: () => null,
    setItem: () => { throw new Error("quota"); },
  });
  const statuses: string[] = [];
  let handlers: ReturnType<typeof useCardPaymentHandlers> | undefined;
  function Probe() {
    handlers = useCardPaymentHandlers({
      cardPayments: {
        immediate_allowed: true,
        calendar_date: "2026-09-17",
        rows: [{ payment_key: "payment-1", payment_parts: [{ entry_payment_key: "payment-1", entry_id: 1, remaining_amount: 500 }] }],
      } as CardPaymentStatus,
      lateEntryForm: { date: "", usagePlace: "", usageItem: "", amount: "" },
      paymentAllocations: { "payment-1": "500" },
      paymentBudget: "",
      setLateEntryForm: vi.fn(),
      setPaymentAllocations: vi.fn(),
      setStatus: (value) => statuses.push(value),
      summary: null,
      userId: 1,
      withRefresh: async () => true,
    });
    return null;
  }
  renderToString(createElement(Probe));
  await handlers!.handleCardPaymentSubmit();
  expect(api.createCardPaymentEvent).not.toHaveBeenCalled();
  expect(statuses.at(-1)).toContain("재시도 정보를 저장할 수 없어");
});

it("releases a definitively rejected payment key so the user can correct the draft", async () => {
  const storage = new Map<string, string>();
  vi.stubGlobal("window", { confirm: () => true });
  vi.stubGlobal("crypto", { randomUUID: () => "fixed-payment-retry-key-0003" });
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  api.createCardPaymentEvent.mockRejectedValueOnce(new ApiResponseError("invalid allocation", 422));
  let handlers: ReturnType<typeof useCardPaymentHandlers> | undefined;
  function Probe() {
    handlers = useCardPaymentHandlers({
      cardPayments: {
        immediate_allowed: true,
        calendar_date: "2026-09-17",
        rows: [{ payment_key: "payment-1", payment_parts: [{ entry_payment_key: "payment-1", entry_id: 1, remaining_amount: 500 }] }],
      } as CardPaymentStatus,
      lateEntryForm: { date: "", usagePlace: "", usageItem: "", amount: "" },
      paymentAllocations: { "payment-1": "500" },
      paymentBudget: "",
      setLateEntryForm: vi.fn(),
      setPaymentAllocations: vi.fn(),
      setStatus: vi.fn(),
      summary: null,
      userId: 1,
      withRefresh: async (action) => {
        try {
          await action();
          return true;
        } catch {
          return false;
        }
      },
    });
    return null;
  }
  renderToString(createElement(Probe));
  await handlers!.handleCardPaymentSubmit();
  expect(storage.size).toBe(0);
  expect(api.createCardPaymentEvent).toHaveBeenCalledTimes(1);
});

it("does not discard the key when the server reports a committed-key payload conflict", async () => {
  const storage = new Map<string, string>();
  vi.stubGlobal("window", { confirm: () => true });
  vi.stubGlobal("crypto", { randomUUID: () => "fixed-payment-retry-key-0004" });
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
  api.createCardPaymentEvent.mockRejectedValueOnce(
    new ApiResponseError("같은 idempotency key에 서로 다른 결제 요청을 사용할 수 없습니다.", 422),
  );
  let handlers: ReturnType<typeof useCardPaymentHandlers> | undefined;
  function Probe() {
    handlers = useCardPaymentHandlers({
      cardPayments: {
        immediate_allowed: true,
        calendar_date: "2026-09-17",
        rows: [{ payment_key: "payment-1", payment_parts: [{ entry_payment_key: "payment-1", entry_id: 1, remaining_amount: 500 }] }],
      } as CardPaymentStatus,
      lateEntryForm: { date: "", usagePlace: "", usageItem: "", amount: "" },
      paymentAllocations: { "payment-1": "500" },
      paymentBudget: "",
      setLateEntryForm: vi.fn(),
      setPaymentAllocations: vi.fn(),
      setStatus: vi.fn(),
      summary: null,
      userId: 1,
      withRefresh: async (action) => {
        try { await action(); return true; } catch { return false; }
      },
    });
    return null;
  }
  renderToString(createElement(Probe));
  await handlers!.handleCardPaymentSubmit();
  expect(storage.size).toBe(1);
});
