import { Dispatch, FormEvent, SetStateAction } from "react";
import {
  CardDiscountMonth,
  CardDiscountPolicy,
  Installment,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  Settings,
  SpendingCategory,
} from "../api";
import { FamilyCardCreditPanel } from "../features/familyCard";
import { CurrentTab } from "../types";
import { DiscountPolicyBar } from "./Insights";
import { EntryTable, InstallmentTable, PanelAppendForm, PanelTable } from "./LedgerTables";
import { currentTabs, formatWon, panelLabel, sumAmounts, today } from "../utils";

type ExpenseForm = { date: string; usagePlace: string; usageItem: string; amount: string };
type InstallmentForm = { title: string; principal: string; fee: string; months: string };
type PanelForm = { panel_type: MonthlyPanel["panel_type"]; title: string; spentOn: string; amount: string; dueDay: string };

export function CurrentMonthView({
  active,
  activeCurrentTab,
  currentSubTabs,
  expenseEntries,
  expenseForm,
  familyDiscountMonth,
  handleCategoryChange,
  handleCurrentEntryDiscount,
  handleCurrentEntryDiscountClear,
  handleDiscountPolicyChange,
  handleEntryDelete,
  handleExpenseSubmit,
  handleInstallmentDelete,
  handleInstallmentSubmit,
  handlePanelComplete,
  handlePanelDelete,
  handlePanelDiscount,
  handlePanelDiscountClear,
  handlePanelShare,
  handlePanelSubmit,
  installmentForm,
  installments,
  isBusy,
  judgment,
  labels,
  ownerDiscountMonth,
  panelForm,
  panels,
  setActiveCurrentTab,
  setExpenseForm,
  setInstallmentForm,
  setPanelForm,
  settings,
}: {
  active: boolean;
  activeCurrentTab: CurrentTab;
  currentSubTabs: { id: CurrentTab; label: string; total: number }[];
  expenseEntries: LedgerEntry[];
  expenseForm: ExpenseForm;
  familyDiscountMonth: CardDiscountMonth | null;
  handleCategoryChange: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  handleCurrentEntryDiscount: (entry: LedgerEntry) => void;
  handleCurrentEntryDiscountClear: (entry: LedgerEntry) => void;
  handleDiscountPolicyChange: (scope: "owner" | "family", month: string, policy: CardDiscountPolicy) => void;
  handleEntryDelete: (entry: LedgerEntry) => void;
  handleExpenseSubmit: (event: FormEvent) => void;
  handleInstallmentDelete: (installment: Installment) => void;
  handleInstallmentSubmit: (event: FormEvent) => void;
  handlePanelComplete: (panelType: "claim" | "family_card") => void;
  handlePanelDelete: (panel: MonthlyPanel) => void;
  handlePanelDiscount: (panel: MonthlyPanel) => void;
  handlePanelDiscountClear: (panel: MonthlyPanel) => void;
  handlePanelShare: (panelType: "claim" | "family_card") => void;
  handlePanelSubmit: (event: FormEvent, panelType: MonthlyPanel["panel_type"]) => Promise<void>;
  installmentForm: InstallmentForm;
  installments: Installment[];
  isBusy: boolean;
  judgment: JudgmentState | null;
  labels: Record<string, string>;
  ownerDiscountMonth: CardDiscountMonth | null;
  panelForm: PanelForm;
  panels: MonthlyPanel[];
  setActiveCurrentTab: Dispatch<SetStateAction<CurrentTab>>;
  setExpenseForm: Dispatch<SetStateAction<ExpenseForm>>;
  setInstallmentForm: Dispatch<SetStateAction<InstallmentForm>>;
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
  settings: Settings;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <nav className="tabs sub-tabs" aria-label="당월 하위 탭">
        {currentSubTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={activeCurrentTab === tab.id ? "active" : ""}
            onClick={() => setActiveCurrentTab(tab.id)}
          >
            <span>{tab.label}</span>
            <strong>{formatWon(tab.total)}</strong>
          </button>
        ))}
      </nav>

      <DiscountPolicyBar
        month={today.slice(0, 7)}
        scope={activeCurrentTab === "family_card" ? "family" : "owner"}
        status={activeCurrentTab === "family_card" ? familyDiscountMonth : ownerDiscountMonth}
        onChange={(scope, month, policy) => handleDiscountPolicyChange(scope, month, policy)}
        isBusy={isBusy}
      />

      <section className={activeCurrentTab === "expenses" ? "tab-panel active" : "tab-panel"}>
        <section className="panel">
          <div className="panel-header">
            <h2>당월 지출</h2>
            <span>{formatWon(sumAmounts(expenseEntries))}</span>
          </div>
          <form className="entry-form" onSubmit={(event) => handleExpenseSubmit(event)}>
            <input
              type="date"
              required
              value={expenseForm.date}
              onChange={(event) => setExpenseForm({ ...expenseForm, date: event.target.value })}
            />
            <input
              required
              value={expenseForm.usagePlace}
              onChange={(event) => setExpenseForm({ ...expenseForm, usagePlace: event.target.value })}
              placeholder="사용처"
            />
            <input
              value={expenseForm.usageItem}
              onChange={(event) => setExpenseForm({ ...expenseForm, usageItem: event.target.value })}
              placeholder="세부내역"
            />
            <input
              required
              type="number"
              min="0"
              step="1"
              value={expenseForm.amount}
              onChange={(event) => setExpenseForm({ ...expenseForm, amount: event.target.value })}
              inputMode="numeric"
              placeholder="금액"
            />
            <button type="submit" disabled={isBusy}>
              추가
            </button>
          </form>
          <EntryTable
            entries={expenseEntries}
            emptyText="당월 지출이 없습니다."
            judgment={judgment}
            onCategoryChange={(entry, category) => handleCategoryChange(entry, category)}
            onDelete={(entry) => handleEntryDelete(entry)}
            discounts={ownerDiscountMonth?.discounts}
            onDiscount={(entry) => handleCurrentEntryDiscount(entry)}
            onClearDiscount={(entry) => handleCurrentEntryDiscountClear(entry)}
            discountPolicy={ownerDiscountMonth?.policy}
            wideDetailColumn
          />
        </section>
      </section>

      {currentTabs
        .filter((tab) => tab !== "expenses")
        .map((tab) => {
          if (tab === "installments") {
            return (
              <section key={tab} className={activeCurrentTab === tab ? "tab-panel active" : "tab-panel"}>
                <InstallmentTable
                  rows={installments}
                  onDelete={(installment) => handleInstallmentDelete(installment)}
                  form={
                    <form className="installment-form" onSubmit={(event) => handleInstallmentSubmit(event)}>
                      <input
                        value={installmentForm.title}
                        onChange={(event) => setInstallmentForm({ ...installmentForm, title: event.target.value })}
                        placeholder="세부내역"
                      />
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={installmentForm.principal}
                        onChange={(event) => setInstallmentForm({ ...installmentForm, principal: event.target.value })}
                        inputMode="numeric"
                        placeholder="할부액"
                      />
                      <input
                        value={installmentForm.fee}
                        onChange={(event) => setInstallmentForm({ ...installmentForm, fee: event.target.value })}
                        inputMode="decimal"
                        placeholder="수수료율(%)"
                      />
                      <input
                        type="number"
                        min="1"
                        value={installmentForm.months}
                        onChange={(event) => setInstallmentForm({ ...installmentForm, months: event.target.value })}
                        placeholder="개월수"
                      />
                      <button type="submit" disabled={isBusy}>
                        추가
                      </button>
                    </form>
                  }
                />
              </section>
            );
          }
          return (
            <section key={tab} className={activeCurrentTab === tab ? "tab-panel active" : "tab-panel"}>
              <PanelTable
                title={panelLabel(labels, tab)}
                rows={panels.filter((panel) => panel.panel_type === tab)}
                onDelete={(panel) => handlePanelDelete(panel)}
                onComplete={tab === "claim" || tab === "family_card" ? () => handlePanelComplete(tab) : undefined}
                onDiscount={tab === "claim" || tab === "family_card" ? (panel) => handlePanelDiscount(panel) : undefined}
                onClearDiscount={tab === "claim" || tab === "family_card" ? (panel) => handlePanelDiscountClear(panel) : undefined}
                discountPolicy={tab === "family_card" ? familyDiscountMonth?.policy : ownerDiscountMonth?.policy}
                judgment={judgment}
                onShare={tab === "claim" || tab === "family_card" ? () => handlePanelShare(tab) : undefined}
                form={
                  <PanelAppendForm
                    isBusy={isBusy}
                    panelType={tab}
                    panelForm={panelForm}
                    setPanelForm={setPanelForm}
                    handlePanelSubmit={handlePanelSubmit}
                  />
                }
              />
              {tab === "family_card" ? (
                <FamilyCardCreditPanel
                  expenseEntries={expenseEntries}
                  installments={installments}
                  judgment={judgment}
                  panels={panels}
                  settings={settings}
                />
              ) : null}
            </section>
          );
        })}
    </section>
  );
}
