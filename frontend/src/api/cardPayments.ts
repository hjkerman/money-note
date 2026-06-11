import { deleteJson, getJson, patchJson, postJson } from "./client";
import { CardDiscountMonth, CardDiscountPolicy, CardPaymentEvent, CardPaymentStatus, LedgerEntry, MonthCloseStatus } from "./types";

export async function fetchCurrentCardPayments(): Promise<CardPaymentStatus> {
  return getJson("/api/card-payments/current");
}

export async function fetchCardDiscountMonth(
  month: string,
  scope: "owner" | "family",
): Promise<CardDiscountMonth> {
  return getJson(`/api/card-discounts/months/${month}?scope=${scope}`);
}

export async function updateCardDiscountPolicy(
  month: string,
  scope: "owner" | "family",
  policy: CardDiscountPolicy,
): Promise<CardDiscountMonth> {
  return patchJson(`/api/card-discounts/months/${month}?scope=${scope}`, { policy });
}

export async function updateEntryDiscount(entryPaymentKey: string, discountAmount: number): Promise<LedgerEntry> {
  return patchJson(`/api/card-discounts/entries/${entryPaymentKey}`, { discount_amount: discountAmount });
}

export async function clearEntryDiscount(entryPaymentKey: string): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-discounts/entries/${entryPaymentKey}`);
}

export async function fetchMonthCloseStatus(): Promise<MonthCloseStatus> {
  return getJson("/api/month/current/status");
}

export async function createCardPaymentEvent(payload: {
  event_date: string;
  event_type: "immediate" | "discount";
  note: string;
  allocations: { entry_payment_key: string; amount_value: number }[];
}): Promise<CardPaymentEvent> {
  return postJson("/api/card-payments/events", payload);
}

export async function deleteCardPaymentEvent(eventId: number): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-payments/events/${eventId}`);
}

export async function acknowledgeLiquidityReset(): Promise<{ payment_month: string }> {
  return postJson("/api/card-payments/acknowledge-liquidity-reset", {});
}

export async function deferTollPayment(entryPaymentKey: string): Promise<{
  entry_payment_key: string;
  from_payment_month: string;
  target_payment_month: string;
}> {
  return postJson(`/api/card-payments/deferrals/${entryPaymentKey}`, {});
}

export async function cancelTollDeferral(entryPaymentKey: string): Promise<{ deleted: boolean }> {
  return deleteJson(`/api/card-payments/deferrals/${entryPaymentKey}`);
}

export async function createLateCardEntry(payload: {
  entry_date: string;
  usage_place: string | null;
  usage_item: string | null;
  amount_value: number;
}): Promise<LedgerEntry> {
  return postJson("/api/card-payments/late-entries", payload);
}
