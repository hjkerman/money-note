import { Dispatch, FormEvent, ReactNode, SetStateAction } from "react";
import { CashFlow, Installment, JudgmentState, LedgerEntry, MonthlyPanel, SpendingCategory } from "../api";
import { PanelType } from "../types";
import {
  categoryLabel,
  formatDateLabel,
  formatMonthLabel,
  formatWon,
  isDiscountExcludedEntry,
  isDiscountExcludedText,
  panelNetAmount,
  sumAmounts,
  sumCashFlows,
  sumInstallmentMonthlyAmounts,
  sumPanelNetAmounts,
  today,
} from "../utils";

type DiscountDraftSetter = Dispatch<SetStateAction<Record<string, string>>>;

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
      className="panel-form"
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
        className={panelType === "claim" || panelType === "settlement" ? "" : "hidden-input"}
        aria-hidden={panelType === "claim" || panelType === "settlement" ? undefined : true}
        tabIndex={panelType === "claim" || panelType === "settlement" ? undefined : -1}
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
        placeholder="적요"
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
  onDiscount,
  onDelete,
  discountDrafts,
  setDiscountDrafts,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  onConfirm: (entry: LedgerEntry) => void;
  onDiscount: (entry: LedgerEntry) => void;
  onDelete: (entry: LedgerEntry) => void;
  discountDrafts: Record<string, string>;
  setDiscountDrafts: DiscountDraftSetter;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>결제일</th>
          <th>사용처</th>
          <th>사용항목</th>
          <th className="amount">금액</th>
          <th className="discount-cell">할인</th>
          <th className="action-cell">확인</th>
          <th className="action-cell">삭제</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id} className={entry.aux_amount_value || isDiscountExcludedEntry(entry) ? "" : "discount-missing-row"}>
            <td className="date">{entry.due_day ? `매월 ${entry.due_day}일` : "날짜 없음"}</td>
            <td>{entry.usage_place ?? ""}</td>
            <td>{entry.usage_item || "좌동"}</td>
            <td className="amount">{formatWon(entry.amount_value)}</td>
            <td className="discount-cell">
              {isDiscountExcludedEntry(entry) ? null : (
                <DiscountEditor
                  currentAmount={entry.aux_amount_value ?? 0}
                  draftKey={`planned:${entry.id}`}
                  drafts={discountDrafts}
                  setDrafts={setDiscountDrafts}
                  onSave={() => onDiscount(entry)}
                />
              )}
            </td>
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
          placeholder="적요"
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
          주 수입
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
              <th>적요</th>
              <th className="amount">금액</th>
              <th className="action-cell">삭제</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="date">{formatDateLabel(row.occurred_on)}</td>
                <td>{row.title}{row.is_primary_income ? <span className="primary-income-badge">주 수입</span> : null}</td>
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
}: {
  months: string[];
  selectedMonth: string;
  setSelectedMonth: (month: string) => void;
  entries: LedgerEntry[];
  judgment: JudgmentState | null;
  onCategoryChange: (entry: LedgerEntry, category: SpendingCategory | null) => void;
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
  discountDrafts = {},
  setDiscountDrafts,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  judgment?: JudgmentState | null;
  onCategoryChange?: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  onDelete?: (entry: LedgerEntry) => void;
  discounts?: Record<string, number>;
  onDiscount?: (entry: LedgerEntry) => void;
  discountDrafts?: Record<string, string>;
  setDiscountDrafts?: DiscountDraftSetter;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>날짜</th>
          <th>사용처</th>
          <th>사용항목</th>
          {onCategoryChange ? <th className="category-cell">분류</th> : null}
          <th className="amount">금액</th>
          {onDiscount ? <th className="discount-cell">할인</th> : null}
          {onDelete ? <th className="action-cell">삭제</th> : null}
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => {
          const selectedCategory = entry.spending_category;
          const currentDiscount = entry.payment_key ? discounts?.[entry.payment_key] ?? 0 : 0;
          const discountEligible = Boolean(onDiscount && entry.payment_key && !isDiscountExcludedEntry(entry));
          return (
            <tr key={entry.id} className={discountEligible && currentDiscount <= 0 ? "discount-missing-row" : ""}>
              <td className="date">{entry.date_label ?? entry.group_label ?? ""}</td>
              <td>{entry.usage_place ?? ""}</td>
              <td>{entry.usage_item ?? ""}</td>
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
                      draftKey={`entry:${entry.id}`}
                      drafts={discountDrafts}
                      setDrafts={setDiscountDrafts}
                      onSave={() => onDiscount(entry)}
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
  draftKey,
  drafts,
  setDrafts,
  onSave,
  disabled = false,
}: {
  currentAmount: number;
  draftKey: string;
  drafts: Record<string, string>;
  setDrafts?: DiscountDraftSetter;
  onSave: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="discount-editor">
      {currentAmount > 0 ? <span className="discount-badge">할인 {formatWon(currentAmount)}</span> : null}
      <div>
        <input
          type="number"
          min="0"
          step="1"
          value={drafts[draftKey] ?? ""}
          onChange={(event) => setDrafts?.((current) => ({ ...current, [draftKey]: event.target.value }))}
          inputMode="numeric"
          placeholder="할인액"
          disabled={disabled}
        />
        <button type="button" onClick={onSave} disabled={disabled}>
          저장
        </button>
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
  discountDrafts = {},
  setDiscountDrafts,
  categoryForPanel,
  judgment,
  form,
}: {
  title: string;
  rows: MonthlyPanel[];
  onDelete?: (panel: MonthlyPanel) => void;
  onReset?: () => void;
  onComplete?: () => void;
  onDiscount?: (panel: MonthlyPanel) => void;
  discountDrafts?: Record<string, string>;
  setDiscountDrafts?: DiscountDraftSetter;
  categoryForPanel?: (panel: MonthlyPanel) => SpendingCategory | null;
  judgment?: JudgmentState | null;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="header-actions">
          <span>{formatWon(sumPanelNetAmounts(rows))}</span>
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
              {(rows.some((row) => row.spent_on) || rows.some((row) => row.panel_type === "claim" || row.panel_type === "settlement")) ? (
                <th>사용일</th>
              ) : null}
              <th>적요</th>
              {categoryForPanel ? <th className="category-cell">자동 분류</th> : null}
              <th className="amount">금액</th>
              {onDiscount ? <th className="discount-cell">할인 / 실제 청구</th> : null}
              {onDelete ? <th className="action-cell">삭제</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const discountEligible = Boolean(onDiscount && !isDiscountExcludedText(row.title));
              return (
              <tr key={row.id} className={discountEligible && row.discount_amount <= 0 ? "discount-missing-row" : ""}>
                {(rows.some((item) => item.spent_on) || rows.some((item) => item.panel_type === "claim" || item.panel_type === "settlement")) ? (
                  <td className="date">{formatDateLabel(row.spent_on ?? "") ?? ""}</td>
                ) : null}
                <td>
                  {row.title}
                </td>
                {categoryForPanel ? (
                  <td className="category-cell">{categoryLabel(categoryForPanel(row), judgment)}</td>
                ) : null}
                <td className="amount">{formatWon(row.amount_value)}</td>
                {onDiscount ? (
                  <td className="discount-cell">
                    {discountEligible ? (
                      <>
                        <DiscountEditor
                          currentAmount={row.discount_amount}
                          draftKey={`panel:${row.id}`}
                          drafts={discountDrafts}
                          setDrafts={setDiscountDrafts}
                          onSave={() => onDiscount(row)}
                        />
                        <span className="net-amount">실제 {formatWon(panelNetAmount(row))}</span>
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
    </section>
  );
}

export function InstallmentTable({
  rows,
  onDelete,
  form,
}: {
  rows: Installment[];
  onDelete: (installment: Installment) => void;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>할부</h2>
        <span>{formatWon(sumInstallmentMonthlyAmounts(rows))}</span>
      </div>
      {form}
      {rows.length ? (
        <table>
          <thead>
            <tr>
              <th>적요</th>
              <th className="amount">할부액</th>
              <th className="amount">수수료율</th>
              <th className="amount">수수료</th>
              <th className="amount">잔여</th>
              <th className="amount">월 납입액</th>
              <th className="action-cell">삭제</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.title}</td>
                <td className="amount">{formatWon(row.principal_amount)}</td>
                <td className="amount">{row.fee_rate.toLocaleString("ko-KR")}%</td>
                <td className="amount">{formatWon(row.fee_amount)}</td>
                <td className="amount">
                  {row.remaining_months}/{row.months}개월
                </td>
                <td className="amount">{formatWon(row.monthly_amount)}</td>
                <td className="action-cell">
                  <button type="button" className="danger" onClick={() => onDelete(row)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">할부 항목이 없습니다.</p>
      )}
    </section>
  );
}
