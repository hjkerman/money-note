import { FormEvent } from "react";
import {
  clearPanelDiscount,
  CardDiscountPolicy,
  completePanelsByType,
  confirmFixedPanel,
  createPanel,
  deleteCashFlow,
  deletePanel,
  MonthlyPanel,
  sharePageUrl,
  updatePanelDiscount,
} from "../api";
import { PanelType } from "../types";
import { focusFirstDataInput, nextSortOrder, panelLabel, panelNetAmount, parseAmount, formatWon } from "../utils";

export function usePanelHandlers({
  familyDiscountPolicy,
  calendarDate,
  labels,
  month,
  ownerDiscountPolicy,
  panelForm,
  panels,
  setPanelForm,
  setStatus,
  withRefresh,
}: {
  familyDiscountPolicy?: CardDiscountPolicy | null;
  calendarDate: string | undefined;
  labels: Record<string, string>;
  month: string | undefined;
  ownerDiscountPolicy?: CardDiscountPolicy | null;
  panelForm: { panel_type: PanelType; title: string; spentOn: string; amount: string; dueDay: string };
  panels: MonthlyPanel[];
  setPanelForm: (value: { panel_type: PanelType; title: string; spentOn: string; amount: string; dueDay: string }) => void;
  setStatus: (value: string) => void;
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  async function handlePanelSubmit(event: FormEvent, panelType = panelForm.panel_type) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!panelForm.title.trim()) return;
    if (!month || !calendarDate) {
      setStatus("서버 기준 날짜를 불러온 뒤 다시 시도하세요.");
      return;
    }
    await withRefresh(async () => {
      const sameTypePanels = panels.filter((panel) => panel.panel_type === panelType);
      await createPanel({
        month,
        panel_type: panelType,
        title: panelForm.title.trim(),
        spent_on:
          panelType === "claim" || panelType === "family_card"
            ? panelForm.spentOn
            : panelType === "frozen"
              ? calendarDate
              : null,
        amount_value: parseAmount(panelForm.amount),
        discount_amount: 0,
        amount_expr: null,
        sort_order: nextSortOrder(sameTypePanels),
        due_day: null,
        confirmed_at: null,
        discount_override: 0,
      });
      setPanelForm({ panel_type: panelType, title: "", spentOn: panelForm.spentOn, amount: "", dueDay: "" });
      setStatus(`${panelLabel(labels, panelType)} 항목 추가 완료`);
      focusFirstDataInput(form);
    });
  }

  async function handlePanelDelete(panel: MonthlyPanel) {
    const isConfirmedFixed =
      panel.panel_type === "fixed" && Boolean(panel.confirmed_at && panel.confirmed_cash_flow_id);
    const confirmed = window.confirm(
      isConfirmedFixed
        ? `${panel.title} 정기지출을 해제할까요?\n\n이미 기록된 현금흐름은 유지됩니다.`
        : `${panel.title} 항목을 삭제할까요?`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePanel(panel.id);
      setStatus(
        isConfirmedFixed
          ? `${panel.title} 정기지출 해제 완료`
          : `${panelLabel(labels, panel.panel_type)} 항목 삭제 완료`,
      );
    });
  }

  async function handleFixedPanelConfirm(panel: MonthlyPanel, occurredOn: string, actualAmount: number) {
    if (panel.panel_type !== "fixed") return;
    if (!Number.isInteger(actualAmount) || actualAmount < 0) {
      setStatus("실제 출금액은 0원 이상의 정수로 입력하세요.");
      return;
    }
    const confirmed = window.confirm(
      `${panel.title}을 ${occurredOn} 현금 지출로 확인 처리할까요?\n\n` +
        `예정액 ${formatWon(panel.amount_value)}\n` +
        `실제 출금액 ${formatWon(actualAmount)}`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      await confirmFixedPanel(panel.id, occurredOn, actualAmount);
      setStatus(`${panel.title} 현금 지출 반영 완료`);
    });
  }

  async function handleFixedPanelConfirmationCancel(panel: MonthlyPanel) {
    if (panel.panel_type !== "fixed" || !panel.confirmed_cash_flow_id) return;
    const confirmed = window.confirm(
      `${panel.title} 확인을 취소할까요?\n\n생성된 현금흐름이 삭제되고 예정액은 다시 미확인 의무로 돌아갑니다.`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteCashFlow(panel.confirmed_cash_flow_id!);
      setStatus(`${panel.title} 확인 취소 완료`);
    });
  }

  async function handlePanelComplete(panelType: "claim" | "family_card") {
    const targetPanels = panels.filter((panel) => panel.panel_type === panelType);
    if (!targetPanels.length) return;
    const confirmed = window.confirm(
      `${panelLabel(labels, panelType)} 항목 ${targetPanels.length}개를 일괄 처리 완료할까요?\n\n현재 목록과 공유 페이지에서 삭제됩니다.`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await completePanelsByType(panelType);
      setStatus(`${panelLabel(labels, panelType)} ${result.completed}개 처리 완료`);
    });
  }

  async function handlePanelProcessSelected(panelType: "claim" | "family_card", selectedPanels: MonthlyPanel[]) {
    if (!selectedPanels.length) return;
    const total = selectedPanels.reduce((sum, panel) => sum + panelNetAmount(panel), 0);
    const confirmed = window.confirm(
      `${panelLabel(labels, panelType)} 항목 ${selectedPanels.length}개, ${formatWon(total)}을 처리 완료할까요?\n\n선택한 항목만 현재 목록과 공유 페이지에서 삭제됩니다.`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      for (const panel of selectedPanels) {
        await deletePanel(panel.id);
      }
      setStatus(`${panelLabel(labels, panelType)} ${selectedPanels.length}개 처리 완료`);
    });
  }

  async function handlePanelShare(panelType: "claim" | "family_card") {
    const url = sharePageUrl(panelType);
    try {
      await navigator.clipboard.writeText(url);
      setStatus(`${panelLabel(labels, panelType)} 공유 링크 복사 완료`);
    } catch {
      window.prompt("공유 링크를 복사하세요.", url);
      setStatus(`${panelLabel(labels, panelType)} 공유 링크 표시 완료`);
    }
  }

  async function handlePanelDiscount(panel: MonthlyPanel) {
    const isFamilyCard = panel.panel_type === "family_card";
    const policy = isFamilyCard ? familyDiscountPolicy : ownerDiscountPolicy;
    if (policy === "disabled") {
      setStatus(`이번 달은 ${isFamilyCard ? "가족카드" : "본인회원 카드"} 할인 혜택이 없는 달로 설정되어 있습니다.`);
      return;
    }
    await withRefresh(async () => {
      await updatePanelDiscount(panel.id, 0);
      setStatus(`${isFamilyCard ? "가족카드" : "청구"} 항목 할인 제외 완료`);
    });
  }

  async function handlePanelDiscountClear(panel: MonthlyPanel) {
    await withRefresh(async () => {
      await clearPanelDiscount(panel.id);
      setStatus(`${panel.panel_type === "family_card" ? "가족카드" : "청구"} 항목 할인 적용 완료`);
    });
  }

  async function handlePanelNetAmountEdit(panel: MonthlyPanel) {
    if (panel.amount_value == null || !["claim", "family_card"].includes(panel.panel_type)) return;
    const currentNet = panelNetAmount(panel);
    const raw = window.prompt("실결제액을 입력하세요.", String(Math.round(currentNet)));
    if (raw === null) return;
    const netAmount = parseAmount(raw);
    if (netAmount === null || netAmount < 0 || netAmount > panel.amount_value) {
      setStatus("실결제액은 0원 이상 원금 이하로 입력해야 합니다.");
      return;
    }
    await withRefresh(async () => {
      await updatePanelDiscount(panel.id, Math.round(panel.amount_value as number) - netAmount);
      setStatus(`실결제액 ${formatWon(netAmount)} 반영 완료`);
    });
  }

  return {
    handlePanelComplete,
    handlePanelDelete,
    handleFixedPanelConfirm,
    handleFixedPanelConfirmationCancel,
    handlePanelDiscount,
    handlePanelDiscountClear,
    handlePanelNetAmountEdit,
    handlePanelProcessSelected,
    handlePanelShare,
    handlePanelSubmit,
  };
}
