import { Dispatch, FormEvent, SetStateAction } from "react";
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
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  function handleAutoAllocate() {
    if (!cardPayments?.immediate_allowed) return;
    let remainingBudget = Math.max(0, parseAmount(paymentBudget) ?? summary?.liquidity_status ?? 0);
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
    if (!cardPayments?.immediate_allowed) return;
    const allocations = Object.entries(paymentAllocations)
      .flatMap(([payment_key, amountText]) => expandCardPaymentAllocation(payment_key, parseAmount(amountText) ?? 0))
      .filter((allocation) => allocation.amount_value > 0);
    if (!allocations.length) return;
    const total = allocations.reduce((sum, allocation) => sum + allocation.amount_value, 0);
    const confirmed = window.confirm(`즉시결제 ${formatWon(total)}을 선택한 사용내역에 반영할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await createCardPaymentEvent({
        event_date: cardPayments.calendar_date,
        event_type: "immediate",
        note: "",
        allocations,
      });
      setPaymentAllocations({});
      setStatus("즉시결제 반영 완료");
    });
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
    const confirmed = window.confirm("실제 계좌 잔액에 맞게 유동성 현황을 보정했습니까?");
    if (!confirmed) return;
    await withRefresh(async () => {
      await acknowledgeLiquidityReset();
      setStatus("유동성 보정 완료 확인");
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
