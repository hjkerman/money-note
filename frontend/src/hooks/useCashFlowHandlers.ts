import { FormEvent } from "react";
import { CashFlow, createCashFlow, deleteCashFlow } from "../api";
import { focusFirstDataInput, nextSortOrder, parseAmount } from "../utils";

export function useCashFlowHandlers({
  cashFlowForm,
  cashFlows,
  setCashFlowForm,
  setStatus,
  withRefresh,
}: {
  cashFlowForm: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
  cashFlows: CashFlow[];
  setCashFlowForm: (value: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean }) => void;
  setStatus: (value: string) => void;
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  async function handleCashFlowSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!cashFlowForm.title.trim()) return;
    const parsed = parseAmount(cashFlowForm.amount);
    if (parsed === null) return;
    await withRefresh(async () => {
      await createCashFlow({
        occurred_on: cashFlowForm.occurredOn,
        title: cashFlowForm.title.trim(),
        amount_value: cashFlowForm.direction === "out" ? -Math.abs(parsed) : Math.abs(parsed),
        sort_order: nextSortOrder(cashFlows),
        is_primary_income: cashFlowForm.direction === "in" && cashFlowForm.isPrimaryIncome ? 1 : 0,
      });
      setCashFlowForm({ ...cashFlowForm, title: "", amount: "" });
      setStatus("현금흐름 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleCashFlowDelete(flow: CashFlow) {
    const confirmed = window.confirm(`${flow.title} 현금흐름 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteCashFlow(flow.id);
      setStatus("현금흐름 삭제 완료");
    });
  }

  return { handleCashFlowDelete, handleCashFlowSubmit };
}
