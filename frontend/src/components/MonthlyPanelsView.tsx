import { Dispatch, FormEvent, SetStateAction } from "react";
import { CashFlow, LedgerEntry, MonthlyPanel, Summary } from "../api";
import { CashFlowPanel, PanelAppendForm, PanelTable, PlannedTable } from "./LedgerTables";
import { panelLabel, formatWon } from "../utils";

type CashFlowForm = { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
type PanelForm = { panel_type: MonthlyPanel["panel_type"]; title: string; spentOn: string; amount: string; dueDay: string };
type PlannedForm = { dueDay: string; usagePlace: string; usageItem: string; amount: string };

export function FixedPanelView({
  active,
  currentMonth,
  handlePanelDelete,
  handlePanelSubmit,
  handlePlannedConfirm,
  handlePlannedDelete,
  handlePlannedSubmit,
  isBusy,
  labels,
  panelForm,
  panels,
  confirmedPlannedEntries,
  plannedEntries,
  plannedForm,
  setPanelForm,
  setPlannedForm,
  summary,
}: {
  active: boolean;
  currentMonth: string;
  handlePanelDelete: (panel: MonthlyPanel) => void;
  handlePanelSubmit: (event: FormEvent, panelType: MonthlyPanel["panel_type"]) => Promise<void>;
  handlePlannedConfirm: (entry: LedgerEntry, entryDate?: string) => void;
  handlePlannedDelete: (entry: LedgerEntry) => void;
  handlePlannedSubmit: (event: FormEvent) => void;
  isBusy: boolean;
  labels: Record<string, string>;
  panelForm: PanelForm;
  panels: MonthlyPanel[];
  confirmedPlannedEntries: LedgerEntry[];
  plannedEntries: LedgerEntry[];
  plannedForm: PlannedForm;
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
  setPlannedForm: Dispatch<SetStateAction<PlannedForm>>;
  summary: Summary | null;
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
          <span>{formatWon(summary?.planned_recurring_total ?? 0)}</span>
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
          month={currentMonth}
          onConfirm={(entry, entryDate) => handlePlannedConfirm(entry, entryDate)}
          onDelete={(entry) => handlePlannedDelete(entry)}
        />
        <ConfirmedPlannedList entries={confirmedPlannedEntries} onUnsubscribe={(entry) => handlePlannedDelete(entry)} />
      </section>
    </section>
  );
}

function ConfirmedPlannedList({ entries, onUnsubscribe }: { entries: LedgerEntry[]; onUnsubscribe: (entry: LedgerEntry) => void }) {
  if (!entries.length) return null;
  return (
    <section className="confirmed-planned-list">
      <div className="panel-subheader">
        <h3>이번 달 처리된 정기결제</h3>
        <span>{entries.length}건</span>
      </div>
      <table>
        <thead>
          <tr>
            <th>결제일</th>
            <th>사용처</th>
            <th>세부내역</th>
            <th>승인일</th>
            <th className="amount">금액</th>
            <th className="action-cell">구독중지</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => (
            <tr key={entry.id}>
              <td className="date">{entry.due_day ? `매월 ${entry.due_day}일` : "날짜 없음"}</td>
              <td>{entry.usage_place ?? ""}</td>
              <td>{entry.usage_item || "좌동"}</td>
              <td className="date">{confirmedPlannedDate(entry)}</td>
              <td className="amount">{formatWon(entry.amount_value)}</td>
              <td className="action-cell">
                <button type="button" className="danger" onClick={() => onUnsubscribe(entry)}>
                  구독중지
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}

function confirmedPlannedDate(entry: LedgerEntry): string {
  if (entry.entry_date) return entry.entry_date;
  if (entry.confirmed_at) return entry.confirmed_at.slice(0, 10);
  return "-";
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
  onOpenHistory,
  setCashFlowForm,
  summary,
}: {
  active: boolean;
  cashFlowForm: CashFlowForm;
  cashFlows: CashFlow[];
  handleCashFlowDelete: (flow: CashFlow) => void;
  handleCashFlowSubmit: (event: FormEvent) => Promise<void>;
  isBusy: boolean;
  onOpenHistory: () => void;
  setCashFlowForm: Dispatch<SetStateAction<CashFlowForm>>;
  summary: Summary | null;
}) {
  return (
    <section className={active ? "tab-panel active" : "tab-panel"}>
      <CashFlowPanel
        rows={cashFlows}
        total={summary?.visible_cash_flow_total ?? 0}
        form={cashFlowForm}
        setForm={setCashFlowForm}
        onSubmit={handleCashFlowSubmit}
        onDelete={(flow) => handleCashFlowDelete(flow)}
        onOpenHistory={onOpenHistory}
        isBusy={isBusy}
      />
    </section>
  );
}
