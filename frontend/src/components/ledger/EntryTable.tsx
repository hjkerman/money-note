import { JudgmentState, LedgerEntry, SpendingCategory } from "../../api";
import {
  categoryLabel,
  displayEntryDateLabel,
  downloadLedgerEntriesMarkdown,
  effectiveEntryDiscount,
  formatWon,
} from "../../utils";
import { DiscountEditor } from "./DiscountEditor";

export function EntryTable({
  entries,
  emptyText,
  judgment,
  onCategoryChange,
  onDelete,
  onDiscount,
  onClearDiscount,
  onNetAmountEdit,
  exportMonth,
  wideDetailColumn = false,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  judgment?: JudgmentState | null;
  onCategoryChange?: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  onDelete?: (entry: LedgerEntry) => void;
  onDiscount?: (entry: LedgerEntry) => void;
  onClearDiscount?: (entry: LedgerEntry) => void;
  onNetAmountEdit?: (entry: LedgerEntry) => void;
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
            const currentDiscount = effectiveEntryDiscount(entry);
            const defaultDiscount = entry.automatic_discount_amount;
            const discountOverride = Boolean(entry.discount_override);
            const discountControlEligible = Boolean(
              onDiscount && entry.payment_key && entry.automatic_discount_eligible,
            );
            const discountDisplayEligible = Boolean(
              discountControlEligible || (onDiscount && discountOverride),
            );
            return (
              <tr key={entry.id}>
                <td className="date entry-date-cell">{displayEntryDateLabel(entry)}</td>
                <td className="entry-place-cell">{entry.usage_place ?? ""}</td>
                <td className="entry-detail-cell">
                  <span className="entry-detail-text">{entry.usage_item ?? ""}</span>
                  {entry.is_transport ? <span className="toll-badge">교통</span> : null}
                  {entry.is_toll ? <span className="toll-badge">통행료</span> : null}
                </td>
                {onCategoryChange ? (
                  <td className="category-cell">
                    <select
                      value={selectedCategory ?? ""}
                      onChange={(event) =>
                        onCategoryChange(
                          entry,
                          (event.target.value || null) as SpendingCategory | null,
                        )
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
                    <button
                      type="button"
                      className="amount-cell-button"
                      onClick={() => onNetAmountEdit(entry)}
                    >
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
                        disabled={entry.discount_policy === "disabled"}
                      />
                    ) : discountDisplayEligible ? (
                      <span
                        className={
                          currentDiscount > 0
                            ? "discount-badge"
                            : "discount-badge muted-discount-badge"
                        }
                      >
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
