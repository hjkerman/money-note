import { FormEvent, ReactNode } from "react";
import { CardDiscountPolicy, CashFlow, JudgmentState, LedgerEntry, MonthlyPanel, SpendingCategory } from "../api";
import { PanelType } from "../types";
import {
  categoryLabel,
  defaultCardDiscount,
  discountIneligibleTitle,
  displayEntryTitle,
  effectiveEntryDiscount,
  effectivePanelDiscount,
  formatDateLabel,
  formatMonthLabel,
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
  onConfirm,
  onDelete,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  onConfirm: (entry: LedgerEntry) => void;
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
          <th className="amount">금액</th>
          <th className="action-cell">확인</th>
          <th className="action-cell">삭제</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id}>
            <td className="date">{entry.due_day ? `매월 ${entry.due_day}일` : "날짜 없음"}</td>
            <td>{entry.usage_place ?? ""}</td>
            <td>{entry.usage_item || "좌동"}</td>
            <td className="amount">{formatWon(entry.amount_value)}</td>
            <td className="action-cell">
              <button type="button" onClick={() => onConfirm(entry)}>
                확인
              </button>
            </td>
            <td className="action-cell">
              <button type="button" className="danger" onClick={() => onDelete(entry)}>
                삭제
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function CashFlowPanel({
  rows,
  form,
  setForm,
  onSubmit,
  onDelete,
  isBusy,
}: {
  rows: CashFlow[];
  form: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
  setForm: (value: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean }) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  onDelete: (flow: CashFlow) => void;
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
    </section>
  );
}

export function HistoryPanel({
  months,
  selectedMonth,
  setSelectedMonth,
  entries,
  judgment,
  onCategoryChange,
  onDelete,
}: {
  months: string[];
  selectedMonth: string;
  setSelectedMonth: (month: string) => void;
  entries: LedgerEntry[];
  judgment: JudgmentState | null;
  onCategoryChange: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  onDelete?: (entry: LedgerEntry) => void;
}) {
  return (
    <section className="panel history-panel">
      <div className="panel-header history-header">
        <div>
          <h2>월별 기록</h2>
          <p>{entries.length ? `${entries.length}개 항목` : "구조화된 기록이 없습니다."}</p>
        </div>
        <div className="history-controls">
          <select value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)}>
            {months.map((month) => (
              <option key={month} value={month}>
                {formatMonthLabel(month)}
              </option>
            ))}
          </select>
          <span>{formatWon(sumAmounts(entries))}</span>
        </div>
      </div>
      <EntryTable
        entries={entries}
        emptyText="이 달의 구조화된 기록이 없습니다."
        judgment={judgment}
        onCategoryChange={onCategoryChange}
        onDelete={onDelete}
      />
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
  discountPolicy = "enabled",
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
  discountPolicy?: CardDiscountPolicy | null;
  wideDetailColumn?: boolean;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
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
          const discountEligible = Boolean(onDiscount && entry.payment_key && !discountIneligibleTitle(displayEntryTitle(entry)));
          const discountOverride = Boolean(entry.discount_override);
          return (
            <tr key={entry.id}>
              <td className="date entry-date-cell">{entry.date_label ?? entry.group_label ?? ""}</td>
              <td className="entry-place-cell">{entry.usage_place ?? ""}</td>
              <td className="entry-detail-cell">{entry.usage_item ?? ""}</td>
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
              <td className="amount">{formatWon(entry.amount_value)}</td>
              {onDiscount ? (
                <td className="discount-cell">
                  {discountEligible ? (
                    <DiscountEditor
                      currentAmount={currentDiscount}
                      defaultAmount={defaultDiscount}
                      isOverride={discountOverride}
                      onExclude={() => onDiscount(entry)}
                      onClear={onClearDiscount ? () => onClearDiscount(entry) : undefined}
                      disabled={discountPolicy === "disabled"}
                    />
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
  );
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
  const badgeText = disabled
    ? "혜택 없음"
    : isOverride
      ? currentAmount > 0
        ? `기록 할인 ${formatWon(currentAmount)}`
        : "할인 제외"
      : `할인 ${formatWon(defaultAmount)}`;
  return (
    <div className="discount-editor">
      <div>
        <button type="button" className="discount-badge" onClick={onClear} disabled={disabled || !isOverride || !onClear}>
          {badgeText}
        </button>
        {!disabled && isOverride ? (
          <button type="button" onClick={onClear} disabled={!onClear}>
            할인 적용
          </button>
        ) : null}
        {!disabled && !isOverride ? (
          <button type="button" onClick={onExclude}>
            제외
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
  discountPolicy?: CardDiscountPolicy | null;
  judgment?: JudgmentState | null;
  onShare?: () => void;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="header-actions">
          <span>{formatWon(sumPanelNetAmounts(rows, discountPolicy))}</span>
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
              {(rows.some((row) => row.spent_on) || rows.some((row) => row.panel_type === "claim" || row.panel_type === "family_card")) ? (
                <th>사용일</th>
              ) : null}
              <th className="panel-title-cell">세부내역</th>
              <th className="amount">금액</th>
              {onDiscount ? <th className="discount-cell">할인 / 원금</th> : null}
              {onDelete ? <th className="action-cell">삭제</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const discountEligible = Boolean(onDiscount && !discountIneligibleTitle(row.title));
              const currentDiscount = effectivePanelDiscount(row, discountPolicy);
              const defaultDiscount = defaultCardDiscount(row.amount_value);
              const discountOverride = Boolean(row.discount_override);
              return (
              <tr key={row.id}>
                {(rows.some((item) => item.spent_on) || rows.some((item) => item.panel_type === "claim" || item.panel_type === "family_card")) ? (
                  <td className="date">{formatDateLabel(row.spent_on ?? "") ?? ""}</td>
                ) : null}
                <td className="panel-title-cell">
                  {row.title}
                </td>
                <td className="amount">{formatWon(discountEligible ? panelNetAmount(row, discountPolicy) : row.amount_value)}</td>
                {onDiscount ? (
                  <td className="discount-cell">
                    {discountEligible ? (
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
