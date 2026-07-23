import { FormEvent, useMemo } from "react";

import { CashFlow, JudgmentState, LedgerEntry } from "../../api";
import { formatDateLabel, formatWon, sumAmounts } from "../../utils";
import { EntryTable } from "./EntryTable";

export function CashFlowPanel({
  rows,
  total,
  form,
  setForm,
  onSubmit,
  onDelete,
  onOpenHistory,
  isBusy,
}: {
  rows: CashFlow[];
  total: number;
  form: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
  setForm: (value: {
    occurredOn: string;
    direction: string;
    title: string;
    amount: string;
    isPrimaryIncome: boolean;
  }) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  onDelete: (flow: CashFlow) => void;
  onOpenHistory: () => void;
  isBusy: boolean;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>현금흐름</h2>
        <span>{formatWon(total)}</span>
      </div>
      <form className="cash-flow-form" onSubmit={(event) => void onSubmit(event)}>
        <input
          type="date"
          value={form.occurredOn}
          onChange={(event) => setForm({ ...form, occurredOn: event.target.value })}
        />
        <select
          value={form.direction}
          onChange={(event) => setForm({ ...form, direction: event.target.value })}
        >
          <option value="in">입금</option>
          <option value="out">출금</option>
        </select>
        <input
          value={form.title}
          onChange={(event) => setForm({ ...form, title: event.target.value })}
          placeholder="세부내역"
        />
        <input
          type="number"
          min="0"
          step="1"
          value={form.amount}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
          inputMode="numeric"
          placeholder="금액"
        />
        <label className="check-label">
          <input
            type="checkbox"
            checked={form.isPrimaryIncome}
            disabled={form.direction !== "in"}
            onChange={(event) => setForm({ ...form, isPrimaryIncome: event.target.checked })}
          />
          이달 기준 수입
        </label>
        <button type="submit" disabled={isBusy}>
          추가
        </button>
      </form>
      {rows.length ? (
        <table>
          <thead>
            <tr>
              <th>날짜</th>
              <th className="panel-title-cell">세부내역</th>
              <th className="amount">금액</th>
              <th className="action-cell">삭제</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="date">{formatDateLabel(row.occurred_on)}</td>
                <td>
                  {row.title}
                  {row.is_primary_income ? (
                    <span className="primary-income-badge">이달 기준 수입</span>
                  ) : null}
                </td>
                <td className={row.amount_value < 0 ? "amount negative" : "amount positive"}>
                  {formatWon(row.amount_value)}
                </td>
                <td className="action-cell">
                  <button type="button" onClick={() => onDelete(row)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">현금 입출금 기록이 없습니다.</p>
      )}
      <button type="button" className="cash-history-button" onClick={onOpenHistory}>
        전체 현금흐름 보기
      </button>
    </section>
  );
}

export function HistoryPanel({
  selectedMonth,
  entries,
  judgment,
}: {
  selectedMonth: string;
  entries: LedgerEntry[];
  judgment: JudgmentState | null;
}) {
  return (
    <section className="panel history-panel">
      <div className="panel-header history-header">
        <div>
          <h2>월별 기록</h2>
          <p>{entries.length ? `${entries.length}개 항목` : "구조화된 기록이 없습니다."}</p>
        </div>
        <div className="history-controls">
          <span>{formatWon(sumAmounts(entries))}</span>
        </div>
      </div>
      <EntryTable
        entries={entries}
        emptyText="이 달의 구조화된 기록이 없습니다."
        judgment={judgment}
        exportMonth={selectedMonth}
      />
    </section>
  );
}

export function CashFlowHistoryPanel({
  rows,
  selectedMonth,
}: {
  rows: CashFlow[];
  selectedMonth: string;
}) {
  const monthlyRows = useMemo(
    () =>
      rows
        .filter((row) => row.occurred_on.startsWith(selectedMonth))
        .sort(
          (a, b) =>
            a.occurred_on.localeCompare(b.occurred_on) ||
            a.sort_order - b.sort_order ||
            a.id - b.id,
        ),
    [rows, selectedMonth],
  );
  return (
    <section className="panel history-panel cash-history-panel">
      <div className="panel-header history-header">
        <div>
          <h2>현금흐름</h2>
          <p>{monthlyRows.length ? `${monthlyRows.length}개 항목` : "현금 입출금 기록이 없습니다."}</p>
        </div>
      </div>
      {monthlyRows.length ? (
        <table>
          <thead>
            <tr>
              <th className="date">일자</th>
              <th>내용</th>
              <th className="amount">금액</th>
            </tr>
          </thead>
          <tbody>
            {monthlyRows.map((row) => (
              <tr key={row.id}>
                <td className="date">{formatDateLabel(row.occurred_on)}</td>
                <td>{row.title}</td>
                <td className={`amount ${row.amount_value < 0 ? "negative" : "positive"}`}>
                  {row.amount_value < 0 ? "-" : "+"}
                  {formatWon(Math.abs(row.amount_value))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">이 달의 현금 입출금 기록이 없습니다.</p>
      )}
    </section>
  );
}
