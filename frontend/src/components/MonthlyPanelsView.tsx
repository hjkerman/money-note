import { Dispatch, FormEvent, SetStateAction } from "react";
import { CashFlow, LedgerEntry, MonthlyPanel } from "../api";
import { CashFlowPanel, PanelAppendForm, PanelTable, PlannedTable } from "./LedgerTables";
import { panelLabel, formatWon, sumAmounts } from "../utils";

type CashFlowForm = { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
type PanelForm = { panel_type: MonthlyPanel["panel_type"]; title: string; spentOn: string; amount: string; dueDay: string };
type PlannedForm = { dueDay: string; usagePlace: string; usageItem: string; amount: string };

export function FixedPanelView({
  active,
  handlePanelDelete,
  handlePanelSubmit,
  handlePlannedConfirm,
  handlePlannedDelete,
  handlePlannedSubmit,
  isBusy,
  labels,
  panelForm,
  panels,
  plannedEntries,
  plannedForm,
  setPanelForm,
  setPlannedForm,
}: {
  active: boolean;
  handlePanelDelete: (panel: MonthlyPanel) => void;
  handlePanelSubmit: (event: FormEvent, panelType: MonthlyPanel["panel_type"]) => Promise<void>;
  handlePlannedConfirm: (entry: LedgerEntry) => void;
  handlePlannedDelete: (entry: LedgerEntry) => void;
  handlePlannedSubmit: (event: FormEvent) => void;
  isBusy: boolean;
  labels: Record<string, string>;
  panelForm: PanelForm;
  panels: MonthlyPanel[];
  plannedEntries: LedgerEntry[];
  plannedForm: PlannedForm;
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
  setPlannedForm: Dispatch<SetStateAction<PlannedForm>>;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <PanelTable
        title={panelLabel(labels, "fixed")}
        rows={panels.filter((panel) => panel.panel_type === "fixed")}
        onDelete={(panel) => handlePanelDelete(panel)}
        form={
          <PanelAppendForm
            isBusy={isBusy}
            panelType="fixed"
            panelForm={panelForm}
            setPanelForm={setPanelForm}
            handlePanelSubmit={handlePanelSubmit}
          />
        }
      />
      <section className="panel">
        <div className="panel-header">
          <h2>카드 정기결제</h2>
          <span>{formatWon(sumAmounts(plannedEntries))}</span>
        </div>
        <form className="planned-form" onSubmit={(event) => handlePlannedSubmit(event)}>
          <input
            type="number"
            min="1"
            max="31"
            required
            value={plannedForm.dueDay}
            onChange={(event) => setPlannedForm({ ...plannedForm, dueDay: event.target.value })}
            placeholder="결제일"
          />
          <input
            required
            value={plannedForm.usagePlace}
            onChange={(event) => setPlannedForm({ ...plannedForm, usagePlace: event.target.value })}
            placeholder="사용처"
          />
          <input
            value={plannedForm.usageItem}
            onChange={(event) => setPlannedForm({ ...plannedForm, usageItem: event.target.value })}
            placeholder="세부내역"
          />
          <input
            required
            type="number"
            min="0"
            step="1"
            value={plannedForm.amount}
            onChange={(event) => setPlannedForm({ ...plannedForm, amount: event.target.value })}
            inputMode="numeric"
            placeholder="금액"
          />
          <button type="submit" disabled={isBusy}>
            추가
          </button>
        </form>
        <PlannedTable
          entries={plannedEntries}
          emptyText="카드 정기결제 항목이 없습니다."
          onConfirm={(entry) => handlePlannedConfirm(entry)}
          onDelete={(entry) => handlePlannedDelete(entry)}
        />
      </section>
    </section>
  );
}

export function FrozenPanelView({
  active,
  handlePanelDelete,
  handlePanelSubmit,
  isBusy,
  labels,
  panelForm,
  panels,
  setPanelForm,
}: {
  active: boolean;
  handlePanelDelete: (panel: MonthlyPanel) => void;
  handlePanelSubmit: (event: FormEvent, panelType: MonthlyPanel["panel_type"]) => Promise<void>;
  isBusy: boolean;
  labels: Record<string, string>;
  panelForm: PanelForm;
  panels: MonthlyPanel[];
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <PanelTable
        title={panelLabel(labels, "frozen")}
        rows={panels.filter((panel) => panel.panel_type === "frozen")}
        onDelete={(panel) => handlePanelDelete(panel)}
        form={
          <PanelAppendForm
            isBusy={isBusy}
            panelType="frozen"
            panelForm={panelForm}
            setPanelForm={setPanelForm}
            handlePanelSubmit={handlePanelSubmit}
          />
        }
      />
    </section>
  );
}

export function CashFlowView({
  active,
  cashFlowForm,
  cashFlows,
  handleCashFlowDelete,
  handleCashFlowSubmit,
  isBusy,
  setCashFlowForm,
}: {
  active: boolean;
  cashFlowForm: CashFlowForm;
  cashFlows: CashFlow[];
  handleCashFlowDelete: (flow: CashFlow) => void;
  handleCashFlowSubmit: (event: FormEvent) => Promise<void>;
  isBusy: boolean;
  setCashFlowForm: Dispatch<SetStateAction<CashFlowForm>>;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <CashFlowPanel
        rows={cashFlows}
        form={cashFlowForm}
        setForm={setCashFlowForm}
        onSubmit={handleCashFlowSubmit}
        onDelete={(flow) => handleCashFlowDelete(flow)}
        isBusy={isBusy}
      />
    </section>
  );
}
