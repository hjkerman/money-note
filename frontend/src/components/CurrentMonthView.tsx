import { Dispatch, FormEvent, SetStateAction } from "react";
import {
  CardDiscountMonth,
  CardDiscountPolicy,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  Settings,
  SpendingCategory,
  Summary,
} from "../api";
import { FamilyCardCreditPanel } from "../features/familyCard";
import { CurrentTab } from "../types";
import { DiscountPolicyBar } from "./Insights";
import { EntryTable, PanelAppendForm, PanelTable } from "./LedgerTables";
import { categoryLabel, currentTabs, formatWon, panelLabel } from "../utils";

type ExpenseForm = { date: string; usagePlace: string; usageItem: string; spendingCategory: string; amount: string };
type PanelForm = { panel_type: MonthlyPanel["panel_type"]; title: string; spentOn: string; amount: string; dueDay: string };

export function CurrentMonthView({
  active,
  activeCurrentTab,
  currentMonth,
  currentSubTabs,
  expenseEntries,
  expenseForm,
  familyDiscountMonth,
  handleCategoryChange,
  handleCurrentEntryDiscount,
  handleCurrentEntryDiscountClear,
  handleCurrentEntryNetAmountEdit,
  handleDiscountPolicyChange,
  handleEntryDelete,
  handleExpenseSubmit,
  handlePanelComplete,
  handlePanelDelete,
  handlePanelDiscount,
  handlePanelDiscountClear,
  handlePanelNetAmountEdit,
  handlePanelProcessSelected,
  handlePanelShare,
  handlePanelSubmit,
  isBusy,
  judgment,
  labels,
  ownerDiscountMonth,
  panelForm,
  panels,
  setActiveCurrentTab,
  setExpenseForm,
  setPanelForm,
  settings,
  summary,
}: {
  active: boolean;
  activeCurrentTab: CurrentTab;
  currentMonth: string;
  currentSubTabs: { id: CurrentTab; label: string; total: number }[];
  expenseEntries: LedgerEntry[];
  expenseForm: ExpenseForm;
  familyDiscountMonth: CardDiscountMonth | null;
  handleCategoryChange: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  handleCurrentEntryDiscount: (entry: LedgerEntry) => void;
  handleCurrentEntryDiscountClear: (entry: LedgerEntry) => void;
  handleCurrentEntryNetAmountEdit: (entry: LedgerEntry) => void;
  handleDiscountPolicyChange: (scope: "owner" | "family", month: string, policy: CardDiscountPolicy) => void;
  handleEntryDelete: (entry: LedgerEntry) => void;
  handleExpenseSubmit: (event: FormEvent) => void;
  handlePanelComplete: (panelType: "claim" | "family_card") => void;
  handlePanelDelete: (panel: MonthlyPanel) => void;
  handlePanelDiscount: (panel: MonthlyPanel) => void;
  handlePanelDiscountClear: (panel: MonthlyPanel) => void;
  handlePanelNetAmountEdit: (panel: MonthlyPanel) => void;
  handlePanelProcessSelected: (panelType: "claim" | "family_card", selectedPanels: MonthlyPanel[]) => void;
  handlePanelShare: (panelType: "claim" | "family_card") => void;
  handlePanelSubmit: (event: FormEvent, panelType: MonthlyPanel["panel_type"]) => Promise<void>;
  isBusy: boolean;
  judgment: JudgmentState | null;
  labels: Record<string, string>;
  ownerDiscountMonth: CardDiscountMonth | null;
  panelForm: PanelForm;
  panels: MonthlyPanel[];
  setActiveCurrentTab: Dispatch<SetStateAction<CurrentTab>>;
  setExpenseForm: Dispatch<SetStateAction<ExpenseForm>>;
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
  settings: Settings;
  summary: Summary | null;
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
        month={currentMonth}
        scope={activeCurrentTab === "family_card" ? "family" : "owner"}
        status={activeCurrentTab === "family_card" ? familyDiscountMonth : ownerDiscountMonth}
        onChange={(scope, month, policy) => handleDiscountPolicyChange(scope, month, policy)}
        isBusy={isBusy}
      />

      <section className={activeCurrentTab === "expenses" ? "tab-panel active" : "tab-panel"}>
        <section className="panel">
          <div className="panel-header">
            <h2>당월 지출</h2>
            <span>{formatWon(currentSubTabs.find((tab) => tab.id === "expenses")?.total ?? 0)}</span>
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
            <select
              value={expenseForm.spendingCategory}
              onChange={(event) => setExpenseForm({ ...expenseForm, spendingCategory: event.target.value })}
              aria-label="분류"
            >
              <option value="">{categoryLabel(null, judgment)}</option>
              <option value="essential">{categoryLabel("essential", judgment)}</option>
              <option value="questionable">{categoryLabel("questionable", judgment)}</option>
              <option value="dignity">{categoryLabel("dignity", judgment)}</option>
            </select>
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
            onDiscount={(entry) => handleCurrentEntryDiscount(entry)}
            onClearDiscount={(entry) => handleCurrentEntryDiscountClear(entry)}
            onNetAmountEdit={(entry) => handleCurrentEntryNetAmountEdit(entry)}
            exportMonth={currentMonth}
            wideDetailColumn
          />
        </section>
      </section>

      {currentTabs
        .filter((tab) => tab !== "expenses")
        .map((tab) => {
          return (
            <section key={tab} className={activeCurrentTab === tab ? "tab-panel active" : "tab-panel"}>
              <PanelTable
                title={panelLabel(labels, tab)}
                rows={panels.filter((panel) => panel.panel_type === tab)}
                onDelete={(panel) => handlePanelDelete(panel)}
                onComplete={tab === "claim" || tab === "family_card" ? () => handlePanelComplete(tab) : undefined}
                onDiscount={tab === "claim" || tab === "family_card" ? (panel) => handlePanelDiscount(panel) : undefined}
                onClearDiscount={tab === "claim" || tab === "family_card" ? (panel) => handlePanelDiscountClear(panel) : undefined}
                onNetAmountEdit={tab === "claim" || tab === "family_card" ? (panel) => handlePanelNetAmountEdit(panel) : undefined}
                onProcessSelected={tab === "claim" || tab === "family_card" ? (selectedPanels) => handlePanelProcessSelected(tab, selectedPanels) : undefined}
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
                  judgment={judgment}
                  settings={settings}
                  summary={summary}
                />
              ) : null}
            </section>
          );
        })}
    </section>
  );
}
