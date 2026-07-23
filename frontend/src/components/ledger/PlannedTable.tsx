import { useMemo, useState } from "react";

import { LedgerEntry } from "../../api";
import { formatWon } from "../../utils";

export function PlannedTable({
  entries,
  emptyText,
  month,
  onConfirm,
  onDelete,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  month: string;
  onConfirm: (entry: LedgerEntry, entryDate: string) => void;
  onDelete: (entry: LedgerEntry) => void;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>결제일</th>
          <th>사용처</th>
          <th>세부내역</th>
          <th>이번 승인 날짜</th>
          <th className="amount">금액</th>
          <th className="action-cell">확인</th>
          <th className="action-cell">삭제</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <PlannedTableRow
            key={entry.id}
            entry={entry}
            month={month}
            onConfirm={onConfirm}
            onDelete={onDelete}
          />
        ))}
      </tbody>
    </table>
  );
}

function PlannedTableRow({
  entry,
  month,
  onConfirm,
  onDelete,
}: {
  entry: LedgerEntry;
  month: string;
  onConfirm: (entry: LedgerEntry, entryDate: string) => void;
  onDelete: (entry: LedgerEntry) => void;
}) {
  const defaultEntryDate = useMemo(
    () => plannedEntryDefaultDate(month, entry.due_day),
    [entry.due_day, month],
  );
  const [entryDate, setEntryDate] = useState(defaultEntryDate);
  return (
    <tr>
      <td className="date">{entry.due_day ? `매월 ${entry.due_day}일` : "날짜 없음"}</td>
      <td>{entry.usage_place ?? ""}</td>
      <td>{entry.usage_item || "좌동"}</td>
      <td>
        <input
          type="date"
          value={entryDate}
          onChange={(event) => setEntryDate(event.target.value)}
          className="compact-date-input"
        />
      </td>
      <td className="amount">{formatWon(entry.amount_value)}</td>
      <td className="action-cell">
        <button type="button" onClick={() => onConfirm(entry, entryDate)}>
          확인
        </button>
      </td>
      <td className="action-cell">
        <button type="button" className="danger" onClick={() => onDelete(entry)}>
          삭제
        </button>
      </td>
    </tr>
  );
}

function plannedEntryDefaultDate(month: string, dueDay: number | null): string {
  const [yearText, monthText] = month.split("-");
  const year = Number(yearText);
  const monthIndex = Number(monthText);
  if (!year || !monthIndex) return "";
  const lastDay = new Date(year, monthIndex, 0).getDate();
  const day = Math.min(Math.max(dueDay ?? 1, 1), lastDay);
  return `${yearText}-${monthText}-${String(day).padStart(2, "0")}`;
}
