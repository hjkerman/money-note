import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import { CardDiscountPolicy, CashFlow, JudgmentState, LedgerEntry, MonthlyPanel, SpendingCategory } from "../api";
import { PanelType } from "../types";
import {
  categoryLabel,
  defaultCardDiscount,
  discountIneligibleTitle,
  downloadLedgerEntriesMarkdown,
  displayEntryTitle,
  displayEntryDateLabel,
  effectiveEntryDiscount,
  effectivePanelDiscount,
  formatDateLabel,
  formatWon,
  panelNetAmount,
  sumAmounts,
  sumCashFlows,
  sumPanelNetAmounts,
  today,
} from "../utils";

export function PanelAppendForm({
  isBusy,
  panelType,
  panelForm,
  setPanelForm,
  handlePanelSubmit,
}: {
  isBusy: boolean;
  panelType: PanelType;
  panelForm: { panel_type: PanelType; title: string; spentOn: string; amount: string; dueDay: string };
  setPanelForm: (value: { panel_type: PanelType; title: string; spentOn: string; amount: string; dueDay: string }) => void;
  handlePanelSubmit: (event: FormEvent, panelType: PanelType) => Promise<void>;
}) {
  return (
    <form
      className={`panel-form panel-form-${panelType}`}
      onSubmit={(event) => void handlePanelSubmit(event, panelType)}
    >
      <input
        type="date"
        value={panelForm.panel_type === panelType ? panelForm.spentOn : today}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: panelForm.title,
            spentOn: event.target.value,
            amount: panelForm.amount,
            dueDay: panelForm.dueDay,
          })
        }
        className={panelType === "claim" || panelType === "family_card" ? "" : "hidden-input"}
        aria-hidden={panelType === "claim" || panelType === "family_card" ? undefined : true}
        tabIndex={panelType === "claim" || panelType === "family_card" ? undefined : -1}
      />
      <input
        value={panelForm.panel_type === panelType ? panelForm.title : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: event.target.value,
            spentOn: panelForm.spentOn,
            amount: panelForm.amount,
            dueDay: panelForm.dueDay,
          })
        }
        placeholder="세부내역"
      />
      <input
        type="number"
        min="0"
        step="1"
        value={panelForm.panel_type === panelType ? panelForm.amount : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: panelForm.title,
            spentOn: panelForm.spentOn,
            amount: event.target.value,
            dueDay: panelForm.dueDay,
          })
        }
        inputMode="numeric"
        placeholder="금액"
      />
      <button type="submit" disabled={isBusy}>
        추가
      </button>
    </form>
  );
}

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
          <PlannedTableRow key={entry.id} entry={entry} month={month} onConfirm={onConfirm} onDelete={onDelete} />
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
  const defaultEntryDate = useMemo(() => plannedEntryDefaultDate(month, entry.due_day), [entry.due_day, month]);
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
  if (!year || !monthIndex) return today;
  const lastDay = new Date(year, monthIndex, 0).getDate();
  const day = Math.min(Math.max(dueDay ?? 1, 1), lastDay);
  return `${yearText}-${monthText}-${String(day).padStart(2, "0")}`;
}

export function CashFlowPanel({
  rows,
  form,
  setForm,
  onSubmit,
  onDelete,
  onOpenHistory,
  isBusy,
}: {
  rows: CashFlow[];
  form: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
  setForm: (value: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean }) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  onDelete: (flow: CashFlow) => void;
  onOpenHistory: () => void;
  isBusy: boolean;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>현금흐름</h2>
        <span>{formatWon(sumCashFlows(rows))}</span>
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
                <td>{row.title}{row.is_primary_income ? <span className="primary-income-badge">이달 기준 수입</span> : null}</td>
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

export function CashFlowHistoryPanel({ rows, selectedMonth }: { rows: CashFlow[]; selectedMonth: string }) {
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
                  {row.amount_value < 0 ? "-" : "+"}{formatWon(Math.abs(row.amount_value))}
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

export function EntryTable({
  entries,
  emptyText,
  judgment,
  onCategoryChange,
  onDelete,
  discounts,
  onDiscount,
  onClearDiscount,
  onNetAmountEdit,
  discountPolicy = "enabled",
  exportMonth,
  wideDetailColumn = false,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  judgment?: JudgmentState | null;
  onCategoryChange?: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  onDelete?: (entry: LedgerEntry) => void;
  discounts?: Record<string, number>;
  onDiscount?: (entry: LedgerEntry) => void;
  onClearDiscount?: (entry: LedgerEntry) => void;
  onNetAmountEdit?: (entry: LedgerEntry) => void;
  discountPolicy?: CardDiscountPolicy | null;
  exportMonth?: string;
  wideDetailColumn?: boolean;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <div className="entry-table-wrap">
      <table className={wideDetailColumn ? "entry-table entry-table-wide-detail" : "entry-table"}>
        <thead>
          <tr>
            <th className="entry-date-cell">사용 일자</th>
            <th className="entry-place-cell">사용처</th>
            <th className="entry-detail-cell">세부내역</th>
            {onCategoryChange ? <th className="category-cell">분류</th> : null}
            <th className="amount">금액</th>
            {onDiscount ? <th className="discount-cell">할인</th> : null}
            {onDelete ? <th className="action-cell">삭제</th> : null}
          </tr>
        </thead>
        <tbody>
          {entries.map((entry) => {
            const selectedCategory = entry.spending_category;
            const currentDiscount = effectiveEntryDiscount(entry, discounts, discountPolicy);
            const defaultDiscount = defaultCardDiscount(entry.amount_value);
            const discountOverride = Boolean(entry.discount_override);
            const discountControlEligible = Boolean(
              onDiscount && entry.payment_key && !discountIneligibleTitle(displayEntryTitle(entry)),
            );
            const discountDisplayEligible = Boolean(discountControlEligible || (onDiscount && discountOverride));
            return (
              <tr key={entry.id}>
                <td className="date entry-date-cell">{displayEntryDateLabel(entry)}</td>
                <td className="entry-place-cell">{entry.usage_place ?? ""}</td>
                <td className="entry-detail-cell">
                  <span className="entry-detail-text">{entry.usage_item ?? ""}</span>
                  {entryHasTransportLabel(entry) ? <span className="toll-badge">교통</span> : null}
                  {entryHasTollLabel(entry) ? <span className="toll-badge">통행료</span> : null}
                </td>
                {onCategoryChange ? (
                  <td className="category-cell">
                    <select
                      value={selectedCategory ?? ""}
                      onChange={(event) =>
                        onCategoryChange(entry, (event.target.value || null) as SpendingCategory | null)
                      }
                    >
                      <option value="">{categoryLabel(null, judgment)}</option>
                      <option value="essential">{categoryLabel("essential", judgment)}</option>
                      <option value="questionable">{categoryLabel("questionable", judgment)}</option>
                      <option value="dignity">{categoryLabel("dignity", judgment)}</option>
                    </select>
                  </td>
                ) : null}
                <td className="amount">
                  {onNetAmountEdit && entry.payment_key ? (
                    <button type="button" className="amount-cell-button" onClick={() => onNetAmountEdit(entry)}>
                      {formatWon(entry.amount_value)}
                    </button>
                  ) : (
                    formatWon(entry.amount_value)
                  )}
                </td>
                {onDiscount ? (
                  <td className="discount-cell">
                    {discountControlEligible ? (
                      <DiscountEditor
                        currentAmount={currentDiscount}
                        defaultAmount={defaultDiscount}
                        isOverride={discountOverride}
                        onExclude={() => onDiscount(entry)}
                        onClear={onClearDiscount ? () => onClearDiscount(entry) : undefined}
                        disabled={discountPolicy === "disabled"}
                      />
                    ) : discountDisplayEligible ? (
                      <span className={currentDiscount > 0 ? "discount-badge" : "discount-badge muted-discount-badge"}>
                        할인 {formatWon(currentDiscount)}
                      </span>
                    ) : null}
                  </td>
                ) : null}
                {onDelete ? (
                  <td className="action-cell">
                    <button type="button" className="danger" onClick={() => onDelete(entry)}>
                      삭제
                    </button>
                  </td>
                ) : null}
              </tr>
            );
          })}
        </tbody>
      </table>
      {exportMonth ? (
        <button
          type="button"
          className="ledger-export-button"
          onClick={() => downloadLedgerEntriesMarkdown(entries, exportMonth, judgment)}
        >
          Markdown 테이블 다운로드
        </button>
      ) : null}
    </div>
  );
}

function entryHasTransportLabel(entry: LedgerEntry): boolean {
  return displayEntryTitle(entry).includes("교통");
}

function entryHasTollLabel(entry: LedgerEntry): boolean {
  const title = displayEntryTitle(entry);
  return title.includes("통행") || title.includes("하이패스");
}

function DiscountEditor({
  currentAmount,
  defaultAmount,
  isOverride,
  onExclude,
  onClear,
  disabled = false,
}: {
  currentAmount: number;
  defaultAmount: number;
  isOverride: boolean;
  onExclude: () => void;
  onClear?: () => void;
  disabled?: boolean;
}) {
  const hasDiscount = currentAmount > 0;
  const showOverrideDiscount = disabled && isOverride;
  const badgeText = disabled && !showOverrideDiscount
    ? "혜택 없음"
    : `할인 ${formatWon(isOverride ? currentAmount : defaultAmount)}`;
  return (
    <div className="discount-editor">
      <div>
        <span className={(disabled && !showOverrideDiscount) || !hasDiscount ? "discount-badge muted-discount-badge" : "discount-badge"}>
          {badgeText}
        </span>
        {!disabled && hasDiscount ? (
          <button type="button" onClick={onExclude}>
            할인 제외
          </button>
        ) : null}
        {!disabled && !hasDiscount ? (
          <button type="button" onClick={onClear} disabled={!onClear}>
            할인 적용
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function PanelTable({
  title,
  rows,
  onDelete,
  onReset,
  onComplete,
  onDiscount,
  onClearDiscount,
  onNetAmountEdit,
  onProcessSelected,
  discountPolicy = "enabled",
  judgment,
  onShare,
  form,
}: {
  title: string;
  rows: MonthlyPanel[];
  onDelete?: (panel: MonthlyPanel) => void;
  onReset?: () => void;
  onComplete?: () => void;
  onDiscount?: (panel: MonthlyPanel) => void;
  onClearDiscount?: (panel: MonthlyPanel) => void;
  onNetAmountEdit?: (panel: MonthlyPanel) => void;
  onProcessSelected?: (panels: MonthlyPanel[]) => void;
  discountPolicy?: CardDiscountPolicy | null;
  judgment?: JudgmentState | null;
  onShare?: () => void;
  form?: ReactNode;
}) {
  const showDateColumn = rows.some(
    (row) =>
      row.panel_type === "claim" ||
      row.panel_type === "family_card" ||
      (Boolean(row.spent_on) && row.panel_type !== "fixed"),
  );
  const dateColumnLabel =
    rows.length > 0 && rows.every((row) => row.panel_type === "frozen") ? "등록일자" : "사용일";
  const selectable = Boolean(onProcessSelected);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const selectedRows = useMemo(
    () => rows.filter((row) => selectedIds.has(row.id)),
    [rows, selectedIds],
  );
  const selectedTotal = sumPanelNetAmounts(selectedRows, discountPolicy);
  const allSelected = rows.length > 0 && selectedRows.length === rows.length;

  useEffect(() => {
    setSelectedIds((current) => {
      const rowIds = new Set(rows.map((row) => row.id));
      const next = new Set([...current].filter((id) => rowIds.has(id)));
      return next.size === current.size ? current : next;
    });
  }, [rows]);

  function setRowSelected(row: MonthlyPanel, selected: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (selected) {
        next.add(row.id);
      } else {
        next.delete(row.id);
      }
      return next;
    });
  }

  function setAllSelected(selected: boolean) {
    setSelectedIds(selected ? new Set(rows.map((row) => row.id)) : new Set());
  }

  function processSelectedRows() {
    if (!onProcessSelected || !selectedRows.length) return;
    onProcessSelected(selectedRows);
    setSelectedIds(new Set());
  }

  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="header-actions">
          <span>{formatWon(sumPanelNetAmounts(rows, discountPolicy))}</span>
          {onProcessSelected && rows.length ? (
            <button type="button" onClick={processSelectedRows} disabled={!selectedRows.length}>
              {formatWon(selectedTotal)} 결제 처리
            </button>
          ) : null}
          {onComplete && rows.length ? (
            <button type="button" onClick={onComplete}>
              일괄 처리 완료
            </button>
          ) : null}
          {onReset && rows.length ? (
            <button type="button" className="danger" onClick={onReset}>
              초기화
            </button>
          ) : null}
        </div>
      </div>
      {form}
      {rows.length ? (
        <table>
          <thead>
            <tr>
              {selectable ? (
                <th className="select-cell">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    aria-label={`${title} 전체 선택`}
                    onChange={(event) => setAllSelected(event.target.checked)}
                  />
                </th>
              ) : null}
              {showDateColumn ? <th>{dateColumnLabel}</th> : null}
              <th className="panel-title-cell">세부내역</th>
              <th className="amount">금액</th>
              {onDiscount ? <th className="discount-cell">할인 / 원금</th> : null}
              {onDelete ? <th className="action-cell">삭제</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const currentDiscount = effectivePanelDiscount(row, discountPolicy);
              const defaultDiscount = defaultCardDiscount(row.amount_value);
              const discountOverride = Boolean(row.discount_override);
              const discountControlEligible = Boolean(onDiscount && !discountIneligibleTitle(row.title));
              const discountDisplayEligible = Boolean(discountControlEligible || (onDiscount && discountOverride));
              const netAmount = panelNetAmount(row, discountPolicy);
              return (
              <tr key={row.id}>
                {selectable ? (
                  <td className="select-cell">
                    <input
                      type="checkbox"
                      checked={selectedIds.has(row.id)}
                      aria-label={`${row.title} 선택`}
                      onChange={(event) => setRowSelected(row, event.target.checked)}
                    />
                  </td>
                ) : null}
                {showDateColumn ? (
                  <td className="date">{formatDateLabel(row.spent_on ?? "") ?? ""}</td>
                ) : null}
                <td className="panel-title-cell">
                  {row.title}
                </td>
                <td className="amount">
                  {onNetAmountEdit ? (
                    <button type="button" className="amount-cell-button" onClick={() => onNetAmountEdit(row)}>
                      {formatWon(netAmount)}
                    </button>
                  ) : (
                    formatWon(discountDisplayEligible ? netAmount : row.amount_value)
                  )}
                </td>
                {onDiscount ? (
                  <td className="discount-cell">
                    {discountControlEligible ? (
                      <>
                        <DiscountEditor
                          currentAmount={currentDiscount}
                          defaultAmount={defaultDiscount}
                          isOverride={discountOverride}
                          onExclude={() => onDiscount(row)}
                          onClear={onClearDiscount ? () => onClearDiscount(row) : undefined}
                          disabled={discountPolicy === "disabled"}
                        />
                        <span className="net-amount">원금 {formatWon(row.amount_value)}</span>
                      </>
                    ) : discountDisplayEligible ? (
                      <>
                        <span className={currentDiscount > 0 ? "discount-badge" : "discount-badge muted-discount-badge"}>
                          할인 {formatWon(currentDiscount)}
                        </span>
                        <span className="net-amount">원금 {formatWon(row.amount_value)}</span>
                      </>
                    ) : null}
                  </td>
                ) : null}
                {onDelete ? (
                  <td className="action-cell">
                    <button type="button" className="danger" onClick={() => onDelete(row)}>
                      삭제
                    </button>
                  </td>
                ) : null}
              </tr>
              );
            })}
          </tbody>
        </table>
      ) : (
        <p className="empty">항목이 없습니다.</p>
      )}
      {onShare ? (
        <button type="button" className="share-wide-button" onClick={onShare}>
          공유하기
        </button>
      ) : null}
    </section>
  );
}
