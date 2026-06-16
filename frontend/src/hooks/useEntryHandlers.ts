import { FormEvent } from "react";
import {
  appendPlannedEntry,
  confirmPlannedEntry,
  createEntry,
  deleteEntry,
  deletePlannedEntry,
  LedgerEntry,
  SpendingCategory,
  updateEntry,
} from "../api";
import {
  displayEntryTitle,
  focusFirstDataInput,
  formatDateLabel,
  formatUsageTitle,
  nextSortOrder,
  parseAmount,
  parseOptionalDay,
} from "../utils";

export function useEntryHandlers({
  entries,
  expenseForm,
  plannedForm,
  setExpenseForm,
  setPlannedForm,
  setStatus,
  withRefresh,
}: {
  entries: LedgerEntry[];
  expenseForm: { date: string; usagePlace: string; usageItem: string; spendingCategory: string; amount: string };
  plannedForm: { dueDay: string; usagePlace: string; usageItem: string; amount: string };
  setExpenseForm: (value: { date: string; usagePlace: string; usageItem: string; spendingCategory: string; amount: string }) => void;
  setPlannedForm: (value: { dueDay: string; usagePlace: string; usageItem: string; amount: string }) => void;
  setStatus: (value: string) => void;
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const usagePlace = expenseForm.usagePlace.trim();
    const usageItem = expenseForm.usageItem.trim();
    const amount = parseAmount(expenseForm.amount);
    if (!expenseForm.date || !usagePlace || amount === null) {
      setStatus("날짜, 사용처, 금액은 필수입니다.");
      return;
    }
    await withRefresh(async () => {
      const dateLabel = formatDateLabel(expenseForm.date);
      const title = formatUsageTitle(usagePlace, usageItem);
      const created = await createEntry({
        book_section: "current",
        entry_kind: "expense",
        entry_date: expenseForm.date || null,
        date_label: dateLabel,
        group_label: null,
        title,
        usage_place: usagePlace || null,
        usage_item: usageItem || null,
        amount_value: amount,
        amount_expr: null,
        aux_amount_value: null,
        aux_amount_expr: null,
        extra_value: null,
        sort_order: nextSortOrder(entries),
        due_day: null,
        confirmed_at: null,
        spending_category: (expenseForm.spendingCategory || null) as SpendingCategory | null,
        discount_override: 0,
      });
      setExpenseForm({ date: expenseForm.date, usagePlace: "", usageItem: "", spendingCategory: "", amount: "" });
      setStatus(created.book_section === "archive" ? "이미 마감한 달의 전체 기록에 추가 완료" : "당월 기록 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handlePlannedSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const usagePlace = plannedForm.usagePlace.trim();
    const usageItem = plannedForm.usageItem.trim();
    const amount = parseAmount(plannedForm.amount);
    const dueDay = parseOptionalDay(plannedForm.dueDay);
    if (!usagePlace || amount === null || dueDay === null) {
      setStatus("결제일, 사용처, 금액은 필수입니다.");
      return;
    }
    await withRefresh(async () => {
      await appendPlannedEntry({
        title: formatUsageTitle(usagePlace, usageItem),
        usage_place: usagePlace || null,
        usage_item: usageItem || null,
        amount_value: amount,
        due_day: dueDay,
      });
      setPlannedForm({ dueDay: "", usagePlace: "", usageItem: "", amount: "" });
      setStatus("카드 정기결제 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handlePlannedConfirm(entry: LedgerEntry) {
    const dueText = entry.due_day ? `${entry.due_day}일` : "오늘";
    const confirmed = window.confirm(`${entry.title}을 ${dueText} 카드 결제 건으로 당월 지출에 넣을까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await confirmPlannedEntry(entry.id);
      setStatus(`${entry.title} 확인 완료`);
    });
  }

  async function handlePlannedDelete(entry: LedgerEntry) {
    const confirmed = window.confirm(`${displayEntryTitle(entry)} 카드 정기결제 항목을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePlannedEntry(entry.id);
      setStatus("카드 정기결제 삭제 완료");
    });
  }

  async function handleCategoryChange(entry: LedgerEntry, category: SpendingCategory | null) {
    if (category === entry.spending_category) return;
    await withRefresh(async () => {
      await updateEntry(entry.id, { spending_category: category });
      setStatus("분류 저장 완료");
    });
  }

  async function handleEntryDelete(entry: LedgerEntry) {
    const confirmed = window.confirm(`${entry.title} 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteEntry(entry.id);
      setStatus(entry.book_section === "archive" ? "전월 기록 삭제 완료" : "당월 기록 삭제 완료");
    });
  }

  return {
    handleCategoryChange,
    handleEntryDelete,
    handleExpenseSubmit,
    handlePlannedConfirm,
    handlePlannedDelete,
    handlePlannedSubmit,
  };
}
