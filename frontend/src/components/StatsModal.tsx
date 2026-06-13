import { StatsPanel } from "./Insights";
import { HistoryPanel } from "./LedgerTables";
import { JudgmentState, LedgerEntry } from "../api";
import { StatItem } from "../types";

export function StatsModal({
  items,
  judgment,
  months,
  selectedMonth,
  setSelectedMonth,
  entries,
  onClose,
}: {
  items: StatItem[];
  judgment: JudgmentState | null;
  months: string[];
  selectedMonth: string;
  setSelectedMonth: (month: string) => void;
  entries: LedgerEntry[];
  onClose: () => void;
}) {
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
        <div className="insight-stack">
          <StatsPanel items={items} judgment={judgment} month={selectedMonth} />
          <HistoryPanel
            months={months}
            selectedMonth={selectedMonth}
            setSelectedMonth={setSelectedMonth}
            entries={entries}
            judgment={judgment}
          />
        </div>
      </section>
    </div>
  );
}
