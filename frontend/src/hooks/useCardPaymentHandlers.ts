import { Dispatch, FormEvent, SetStateAction, useEffect, useRef, useState } from "react";
import {
  acknowledgeLiquidityReset,
  cancelTollDeferral,
  CardDiscountPolicy,
  CardPaymentRow,
  CardPaymentStatus,
  clearEntryDiscount,
  createCardPaymentEvent,
  createLateCardEntry,
  deleteEntry,
  deferTollPayment,
  LedgerEntry,
  Summary,
  updateCardDiscountPolicy,
  updateEntryDiscount,
} from "../api";
import { ApiResponseError } from "../api/client";
import {
  displayEntryTitle,
  focusFirstDataInput,
  formatMonthLabel,
  formatWon,
  entryNetAmount,
  monthLastDay,
  parseAmount,
  sumPaymentAllocationInputs,
} from "../utils";

export function useCardPaymentHandlers({
  cardPayments,
  lateEntryForm,
  ownerDiscountPolicy,
  paymentAllocations,
  paymentBudget,
  setLateEntryForm,
  setPaymentAllocations,
  setStatus,
  summary,
  userId,
  withRefresh,
}: {
  cardPayments: CardPaymentStatus | null;
  lateEntryForm: { date: string; usagePlace: string; usageItem: string; amount: string };
  ownerDiscountPolicy?: CardDiscountPolicy | null;
  paymentAllocations: Record<string, string>;
  paymentBudget: string;
  setLateEntryForm: (value: { date: string; usagePlace: string; usageItem: string; amount: string }) => void;
  setPaymentAllocations: Dispatch<SetStateAction<Record<string, string>>>;
  setStatus: (value: string) => void;
  summary: Summary | null;
  userId: number | null;
  withRefresh: (action: () => Promise<void>) => Promise<boolean>;
}) {
  const [pendingPaymentRequest, setPendingPaymentRequest] = useState<PendingPayment | "corrupt" | null>(
    () => userId === null ? null : readPendingPayment(userId),
  );
  const pendingPaymentRef = useRef(pendingPaymentRequest);
  const paymentInFlight = useRef(false);
  useEffect(() => {
    const pending = userId === null ? null : readPendingPayment(userId);
    pendingPaymentRef.current = pending;
    setPendingPaymentRequest(pending);
  }, [userId]);

  async function confirmPendingPayment() {
    const pending = pendingPaymentRef.current;
    if (pending === "corrupt") {
      setStatus("이전 결제 재시도 정보를 읽을 수 없습니다. 저장소 복구 후 다시 시도해 주세요.");
      return;
    }
    if (paymentInFlight.current || !userId || !pending) return;
    if (!window.confirm("이전 결제가 서버에 없었다면 지금 원래 금액으로 새로 반영됩니다. 동일 요청을 확인할까요?")) return;
    paymentInFlight.current = true;
    try {
      const confirmed = await withRefresh(async () => {
        await sendPendingPayment(pending, userId);
      });
      if (!confirmed) return;
      try {
        localStorage.removeItem(pendingPaymentStorageKey(userId));
        pendingPaymentRef.current = null;
        setPendingPaymentRequest(null);
        clearOnlySubmittedAllocations(pending);
        setStatus("즉시결제 반영 완료");
      } catch {
        setStatus("즉시결제는 반영됐지만 재시도 정보 정리에 실패했습니다. 다시 확인해 주세요.");
      }
    } finally {
      paymentInFlight.current = false;
    }
  }

  function handleAutoAllocate() {
    if (!cardPayments?.immediate_allowed) return;
    let remainingBudget = Math.max(0, parseAmount(paymentBudget) ?? summary?.cash_flow_balance ?? 0);
    const next: Record<string, string> = {};
    for (const row of cardPayments.rows) {
      if (
        !row.payment_key ||
        row.is_deferred ||
        row.is_transport ||
        row.is_toll ||
        row.remaining_amount <= 0 ||
        remainingBudget <= 0
      ) continue;
      const allocated = Math.min(row.remaining_amount, remainingBudget);
      next[row.payment_key] = String(Math.round(allocated));
      remainingBudget -= allocated;
    }
    setPaymentAllocations(next);
    setStatus(`날짜순 결제안 생성 완료: ${formatWon(sumPaymentAllocationInputs(next))} · 교통/통행료 제외`);
  }

  function handlePaymentSelection(row: CardPaymentRow, selected: boolean) {
    if (!row.payment_key) return;
    setPaymentAllocations((current) => {
      const next = { ...current };
      if (selected) next[row.payment_key as string] = String(Math.round(row.remaining_amount));
      else delete next[row.payment_key as string];
      return next;
    });
  }

  async function handleCardPaymentSubmit() {
    if (!cardPayments?.immediate_allowed || paymentInFlight.current || !userId) return;
    const allocations = Object.entries(paymentAllocations)
      .flatMap(([payment_key, amountText]) => expandCardPaymentAllocation(payment_key, parseAmount(amountText) ?? 0))
      .filter((allocation) => allocation.amount_value > 0);
    if (!allocations.length) return;
    const total = allocations.reduce((sum, allocation) => sum + allocation.amount_value, 0);
    const confirmed = window.confirm(`즉시결제 ${formatWon(total)}을 선택한 사용내역에 반영할까요?`);
    if (!confirmed) return;
    const requestPayload = {
      event_date: cardPayments.calendar_date,
      event_type: "immediate" as const,
      note: "",
      allocations,
    };
    const requestFingerprint = JSON.stringify(requestPayload);
    if (pendingPaymentRef.current === "corrupt") {
      setStatus("이전 결제 재시도 정보를 읽을 수 없습니다. 복구 후 결제를 진행해 주세요.");
      return;
    }
    if (pendingPaymentRef.current && pendingPaymentRef.current.fingerprint !== requestFingerprint) {
      setStatus("이전 미확정 즉시결제를 먼저 확인해야 새 결제를 진행할 수 있습니다.");
      return;
    }
    let pending = pendingPaymentRef.current;
    if (!pending) {
      pending = {
        fingerprint: requestFingerprint,
        key: createIdempotencyKey(),
        payload: requestPayload,
        draftAllocations: { ...paymentAllocations },
      };
      try {
        localStorage.setItem(pendingPaymentStorageKey(userId), JSON.stringify(pending));
      } catch {
        setStatus("재시도 정보를 저장할 수 없어 결제를 시작하지 않았습니다.");
        return;
      }
      pendingPaymentRef.current = pending;
      setPendingPaymentRequest(pending);
    }
    paymentInFlight.current = true;
    try {
      const confirmed = await withRefresh(async () => {
        await sendPendingPayment(pending, userId);
      });
      if (!confirmed) return;
      try {
        localStorage.removeItem(pendingPaymentStorageKey(userId));
        pendingPaymentRef.current = null;
        setPendingPaymentRequest(null);
        clearOnlySubmittedAllocations(pending);
        setStatus("즉시결제 반영 완료");
      } catch {
        setStatus("즉시결제는 반영됐지만 재시도 정보 정리에 실패했습니다. 다시 확인해 주세요.");
      }
    } finally {
      paymentInFlight.current = false;
    }
  }

  async function sendPendingPayment(pending: PendingPayment, paymentUserId: number) {
    try {
      await createCardPaymentEvent({ ...pending.payload, idempotency_key: pending.key });
    } catch (error) {
      // The server checks the idempotency record before validation. A 400/422
      // therefore proves this exact key did not commit, unlike a lost response.
      if (
        error instanceof ApiResponseError &&
        (error.status === 400 || error.status === 422) &&
        !error.message.includes("같은 idempotency key")
      ) {
        try {
          localStorage.removeItem(pendingPaymentStorageKey(paymentUserId));
          pendingPaymentRef.current = null;
          setPendingPaymentRequest(null);
        } catch {
          // Keep the durable record if cleanup fails; never replace its key.
        }
      }
      throw error;
    }
  }

  function clearOnlySubmittedAllocations(pending: PendingPayment) {
    setPaymentAllocations((current) =>
      JSON.stringify(current) === JSON.stringify(pending.draftAllocations) ? {} : current,
    );
  }

  async function handleDiscountPolicyChange(scope: "owner" | "family", month: string, policy: CardDiscountPolicy) {
    await withRefresh(async () => {
      await updateCardDiscountPolicy(month, scope, policy);
      setStatus(`${formatMonthLabel(month)} ${scope === "family" ? "가족카드" : "본인회원 카드"} 할인 혜택 설정 완료`);
    });
  }

  async function handleCurrentEntryDiscount(entry: LedgerEntry) {
    if (!entry.payment_key) return;
    if (ownerDiscountPolicy === "disabled") {
      setStatus("이번 달은 본인회원 카드 할인 혜택이 없는 달로 설정되어 있습니다.");
      return;
    }
    await withRefresh(async () => {
      await updateEntryDiscount(entry.payment_key as string, 0);
      setStatus("당월 사용내역 할인 제외 완료");
    });
  }

  async function handleCurrentEntryDiscountClear(entry: LedgerEntry) {
    if (!entry.payment_key) return;
    await withRefresh(async () => {
      await clearEntryDiscount(entry.payment_key as string);
      setStatus("당월 사용내역 할인 적용 완료");
    });
  }

  async function handleCurrentEntryNetAmountEdit(entry: LedgerEntry) {
    if (!entry.payment_key || entry.amount_value == null) return;
    const currentNet = entryNetAmount(entry);
    const raw = window.prompt("실결제액을 입력하세요.", String(Math.round(currentNet)));
    if (raw === null) return;
    const netAmount = parseAmount(raw);
    if (netAmount === null || netAmount < 0 || netAmount > entry.amount_value) {
      setStatus("실결제액은 0원 이상 원금 이하로 입력해야 합니다.");
      return;
    }
    await withRefresh(async () => {
      await updateEntryDiscount(entry.payment_key as string, Math.round(entry.amount_value as number) - netAmount);
      setStatus(`실결제액 ${formatWon(netAmount)} 반영 완료`);
    });
  }

  async function handleTollDeferral(row: CardPaymentRow, defer: boolean) {
    if (!row.payment_keys.length) return;
    const confirmed = window.confirm(
      defer
        ? `${displayEntryTitle(row)} 항목을 다음 달 결제로 이월할까요?`
        : `${displayEntryTitle(row)} 항목을 이번 달 결제 대상으로 되돌릴까요?`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      for (const paymentKey of row.payment_keys) {
        if (defer) await deferTollPayment(paymentKey);
        else await cancelTollDeferral(paymentKey);
      }
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        return next;
      });
      setStatus(defer ? "카드 사용내역 다음 달 이월 완료" : "카드 사용내역 이번 달 처리 대상으로 복귀");
    });
  }

  async function handleCardPaymentRowDelete(row: CardPaymentRow) {
    const confirmed = window.confirm(`${displayEntryTitle(row)} 항목을 결제 대상과 장부에서 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      for (const entryId of row.entry_ids) {
        await deleteEntry(entryId);
      }
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        return next;
      });
      setStatus(row.is_group ? "묶음 카드 사용내역 삭제 완료" : "카드 사용내역 삭제 완료");
    });
  }

  async function handleCardPaymentDiscountToggle(row: CardPaymentRow, exclude: boolean) {
    const paymentKeys = row.payment_keys.filter(Boolean);
    if (!paymentKeys.length) return;
    await withRefresh(async () => {
      for (const paymentKey of paymentKeys) {
        if (exclude) await updateEntryDiscount(paymentKey, 0);
        else await clearEntryDiscount(paymentKey);
      }
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        for (const paymentKey of paymentKeys) delete next[paymentKey];
        return next;
      });
      setStatus(exclude ? "결제 대상 할인 제외 완료" : "결제 대상 할인 적용 완료");
    });
  }

  async function handleLateEntrySubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const amount = parseAmount(lateEntryForm.amount);
    if (amount === null || amount <= 0 || (!lateEntryForm.usagePlace.trim() && !lateEntryForm.usageItem.trim())) return;
    await withRefresh(async () => {
      await createLateCardEntry({
        entry_date: lateEntryForm.date,
        usage_place: lateEntryForm.usagePlace.trim() || null,
        usage_item: lateEntryForm.usageItem.trim() || null,
        amount_value: amount,
      });
      setLateEntryForm({
        date: cardPayments ? monthLastDay(cardPayments.usage_month) : lateEntryForm.date,
        usagePlace: "",
        usageItem: "",
        amount: "",
      });
      setStatus("전월 매입 지연 내역 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleLiquidityResetAcknowledgement() {
    const confirmed = window.confirm("실제 계좌 잔액에 맞게 현금흐름 반영액을 보정했습니까?");
    if (!confirmed) return;
    await withRefresh(async () => {
      await acknowledgeLiquidityReset();
      setStatus("현금흐름 보정 완료 확인");
    });
  }

  function expandCardPaymentAllocation(paymentKey: string, amount: number) {
    const row = cardPayments?.rows.find((item) => item.payment_key === paymentKey);
    if (!row) return [{ entry_payment_key: paymentKey, amount_value: amount }];
    let remaining = amount;
    const allocations = [];
    for (const part of row.payment_parts ?? []) {
      if (remaining <= 0) break;
      const allocated = Math.min(part.remaining_amount, remaining);
      allocations.push({ entry_payment_key: part.entry_payment_key, amount_value: allocated });
      remaining -= allocated;
    }
    return allocations;
  }

  return {
    handleAutoAllocate,
    handleCardPaymentDiscountToggle,
    handleCardPaymentRowDelete,
    handleCardPaymentSubmit,
    confirmPendingPayment,
    hasPendingPayment: pendingPaymentRequest !== null,
    handleCurrentEntryDiscount,
    handleCurrentEntryDiscountClear,
    handleCurrentEntryNetAmountEdit,
    handleDiscountPolicyChange,
    handleLateEntrySubmit,
    handleLiquidityResetAcknowledgement,
    handlePaymentSelection,
    handleTollDeferral,
  };
}

type PaymentPayload = {
  event_date: string;
  event_type: "immediate";
  note: string;
  allocations: { entry_payment_key: string; amount_value: number }[];
};
type PendingPayment = {
  fingerprint: string;
  key: string;
  payload: PaymentPayload;
  draftAllocations: Record<string, string>;
};

function pendingPaymentStorageKey(userId: number): string {
  return `money-note-pending-card-payment-v1:${userId}`;
}

function readPendingPayment(userId: number): PendingPayment | "corrupt" | null {
  try {
    const raw = localStorage.getItem(pendingPaymentStorageKey(userId));
    if (!raw) return null;
    const pending = JSON.parse(raw) as PendingPayment;
    if (
      typeof pending.key !== "string" ||
      pending.key.length < 16 ||
      typeof pending.fingerprint !== "string" ||
      !pending.payload ||
      !pending.draftAllocations ||
      typeof pending.draftAllocations !== "object" ||
      Array.isArray(pending.draftAllocations) ||
      JSON.stringify(pending.payload) !== pending.fingerprint
    ) return "corrupt";
    return pending;
  } catch {
    return "corrupt";
  }
}

function createIdempotencyKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  return `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
