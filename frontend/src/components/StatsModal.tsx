import { useEffect, useMemo, useRef, useState } from "react";
import { CashFlow, fetchCashFlows, JudgmentState, LedgerEntry } from "../api";
import { StatsView } from "../hooks/useModalState";
import { StatItem } from "../types";
import { formatMonthLabel } from "../utils";
import { StatsPanel } from "./Insights";
import { CashFlowHistoryPanel, HistoryPanel } from "./LedgerTables";

export function StatsModal({
  items,
  judgment,
  months,
  selectedMonth,
  setSelectedMonth,
  entries,
  recentCashFlows,
  view,
  setView,
  onClose,
}: {
  items: StatItem[];
  judgment: JudgmentState | null;
  months: string[];
  selectedMonth: string;
  setSelectedMonth: (month: string) => void;
  entries: LedgerEntry[];
  recentCashFlows: CashFlow[];
  view: StatsView;
  setView: (view: StatsView) => void;
  onClose: () => void;
}) {
  const [allCashFlows, setAllCashFlows] = useState<CashFlow[] | null>(null);
  const [cashFlowError, setCashFlowError] = useState("");
  const requestedCashFlows = useRef(false);

  useEffect(() => {
    if (view !== "cash" || requestedCashFlows.current) return;
    requestedCashFlows.current = true;
    void fetchCashFlows()
      .then((rows) => {
        setAllCashFlows(rows);
      })
      .catch((error) => {
        setCashFlowError(error instanceof Error ? error.message : String(error));
      });
  }, [view]);

  const visibleCashFlows = allCashFlows ?? recentCashFlows;
  const selectableMonths = useMemo(() => {
    const values = new Set(months);
    values.add(selectedMonth);
    for (const row of visibleCashFlows) values.add(row.occurred_on.slice(0, 7));
    return [...values].sort((a, b) => b.localeCompare(a));
  }, [months, selectedMonth, visibleCashFlows]);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="stats-modal"
        role="dialog"
        aria-modal="true"
        aria-label="통계와 월별 기록"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="panel-header">
          <h2>통계와 월별 기록</h2>
          <button type="button" onClick={onClose}>
            닫기
          </button>
        </div>
        <div className="stats-toolbar">
          <select value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)}>
            {selectableMonths.map((month) => (
              <option key={month} value={month}>
                {formatMonthLabel(month)}
              </option>
            ))}
          </select>
          <div className="stats-view-toggle" role="group" aria-label="통계 기록 종류">
            <button type="button" className={view === "card" ? "active" : ""} onClick={() => setView("card")}>
              카드 지출
            </button>
            <button type="button" className={view === "cash" ? "active" : ""} onClick={() => setView("cash")}>
              현금흐름
            </button>
          </div>
        </div>
        <div className="insight-stack">
          {view === "card" ? (
            <>
              <StatsPanel items={items} judgment={judgment} month={selectedMonth} />
              <HistoryPanel selectedMonth={selectedMonth} entries={entries} judgment={judgment} />
            </>
          ) : (
            <>
              {cashFlowError ? <p className="modal-load-error">현금흐름을 불러오지 못했습니다: {cashFlowError}</p> : null}
              {!allCashFlows && !cashFlowError ? <p className="modal-loading">전체 현금흐름을 불러오는 중입니다.</p> : null}
              <CashFlowHistoryPanel rows={visibleCashFlows} selectedMonth={selectedMonth} />
            </>
          )}
        </div>
      </section>
    </div>
  );
}
