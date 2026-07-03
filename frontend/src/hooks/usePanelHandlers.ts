import { FormEvent } from "react";
import {
  clearPanelDiscount,
  CardDiscountPolicy,
  completePanelsByType,
  createPanel,
  deletePanel,
  MonthlyPanel,
  sharePageUrl,
  updatePanelDiscount,
} from "../api";
import { PanelType } from "../types";
import { focusFirstDataInput, nextSortOrder, panelLabel, panelNetAmount, parseAmount, today, formatWon } from "../utils";

export function usePanelHandlers({
  familyDiscountPolicy,
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
    await withRefresh(async () => {
      const sameTypePanels = panels.filter((panel) => panel.panel_type === panelType);
      await createPanel({
        month: month ?? today.slice(0, 7),
        panel_type: panelType,
        title: panelForm.title.trim(),
        spent_on:
          panelType === "claim" || panelType === "family_card"
            ? panelForm.spentOn
            : panelType === "frozen"
              ? today
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
    const confirmed = window.confirm(`${panel.title} 항목을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePanel(panel.id);
      setStatus(`${panelLabel(labels, panel.panel_type)} 항목 삭제 완료`);
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
    const policy = panelType === "family_card" ? familyDiscountPolicy : ownerDiscountPolicy;
    const total = selectedPanels.reduce((sum, panel) => sum + panelNetAmount(panel, policy ?? null), 0);
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
    const policy = panel.panel_type === "family_card" ? familyDiscountPolicy : ownerDiscountPolicy;
    const currentNet = panelNetAmount(panel, policy ?? null);
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
    handlePanelDiscount,
    handlePanelDiscountClear,
    handlePanelNetAmountEdit,
    handlePanelProcessSelected,
    handlePanelShare,
    handlePanelSubmit,
  };
}
