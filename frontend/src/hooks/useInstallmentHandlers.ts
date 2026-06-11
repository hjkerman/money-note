import { FormEvent } from "react";
import { createInstallment, deleteInstallment, Installment } from "../api";
import { focusFirstDataInput, nextSortOrder, parseAmount } from "../utils";

export function useInstallmentHandlers({
  currentMonth,
  installmentForm,
  installments,
  setInstallmentForm,
  setStatus,
  withRefresh,
}: {
  currentMonth: string;
  installmentForm: { title: string; principal: string; fee: string; months: string };
  installments: Installment[];
  setInstallmentForm: (value: { title: string; principal: string; fee: string; months: string }) => void;
  setStatus: (value: string) => void;
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  async function handleInstallmentSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!installmentForm.title.trim()) return;
    const principal = parseAmount(installmentForm.principal);
    const feeRate = Number(installmentForm.fee.replaceAll(",", "").trim() || 0);
    const months = Number(installmentForm.months);
    if (principal === null || !Number.isFinite(feeRate) || !Number.isInteger(months) || months < 1) return;
    await withRefresh(async () => {
      await createInstallment({
        title: installmentForm.title.trim(),
        principal_amount: principal,
        fee_rate: feeRate,
        months,
        remaining_months: months,
        start_month: currentMonth,
        sort_order: nextSortOrder(installments),
      });
      setInstallmentForm({ title: "", principal: "", fee: "0", months: "" });
      setStatus("할부 항목 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleInstallmentDelete(installment: Installment) {
    const confirmed = window.confirm(`${installment.title} 할부 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteInstallment(installment.id);
      setStatus("할부 항목 삭제 완료");
    });
  }

  return { handleInstallmentDelete, handleInstallmentSubmit };
}
