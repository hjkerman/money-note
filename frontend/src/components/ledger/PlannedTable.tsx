import { useEffect, useMemo, useState } from "react";

import { LedgerEntry, PlannedChargePreview, previewPlannedEntry } from "../../api";
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
  onConfirm: (entry: LedgerEntry, entryDate: string, actualAmount: number) => void;
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
          <th>원금</th>
          <th className="amount">할인</th>
          <th className="amount">실결제 예상액</th>
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
  onConfirm: (entry: LedgerEntry, entryDate: string, actualAmount: number) => void;
  onDelete: (entry: LedgerEntry) => void;
}) {
  const defaultEntryDate = useMemo(
    () => plannedEntryDefaultDate(month, entry.due_day),
    [entry.due_day, month],
  );
  const [entryDate, setEntryDate] = useState(defaultEntryDate);
  const [actualAmount, setActualAmount] = useState(String(entry.amount_value ?? 0));
  const [preview, setPreview] = useState<PlannedChargePreview>(() => entryPreview(entry));
  const parsedActualAmount = parseNonNegativeInteger(actualAmount);

  useEffect(() => {
    setActualAmount(String(entry.amount_value ?? 0));
    setPreview(entryPreview(entry));
  }, [entry]);

  async function refreshPreview() {
    if (parsedActualAmount === null) return;
    try {
      setPreview(await previewPlannedEntry(entry.id, parsedActualAmount));
    } catch {
      // 확인 버튼에서도 서버 미리보기를 다시 검증하므로 입력 중 실패는 조용히 유지한다.
    }
  }
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
      <td>
        <input
          type="number"
          min="0"
          step="1"
          value={actualAmount}
          onChange={(event) => setActualAmount(event.target.value)}
          onBlur={() => void refreshPreview()}
          className="compact-money-input"
          aria-label={`${entry.title} 원금`}
        />
      </td>
      <td className="amount">{formatWon(preview.effective_discount_amount)}</td>
      <td className="amount">{formatWon(preview.effective_amount_value)}</td>
      <td className="action-cell">
        <button
          type="button"
          disabled={!entryDate || parsedActualAmount === null}
          onClick={() => parsedActualAmount !== null && onConfirm(entry, entryDate, parsedActualAmount)}
        >
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

function entryPreview(entry: LedgerEntry): PlannedChargePreview {
  return {
    amount_value: entry.amount_value ?? 0,
    discount_policy: entry.discount_policy,
    automatic_discount_eligible: entry.automatic_discount_eligible,
    effective_discount_amount: entry.effective_discount_amount,
    effective_amount_value: entry.effective_amount_value ?? entry.amount_value ?? 0,
  };
}

function parseNonNegativeInteger(value: string): number | null {
  const normalized = value.trim();
  if (!normalized) return null;
  const parsed = Number(normalized);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : null;
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
