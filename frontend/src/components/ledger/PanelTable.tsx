import { ReactNode, useEffect, useMemo, useState } from "react";

import { JudgmentState, MonthlyPanel } from "../../api";
import {
  effectivePanelDiscount,
  formatDateLabel,
  formatWon,
  panelNetAmount,
  sumPanelNetAmounts,
} from "../../utils";
import { DiscountEditor } from "./DiscountEditor";

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
  judgment: _judgment,
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
  const selectedTotal = sumPanelNetAmounts(selectedRows);
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
          <span>{formatWon(sumPanelNetAmounts(rows))}</span>
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
              const currentDiscount = effectivePanelDiscount(row);
              const defaultDiscount = row.automatic_discount_amount;
              const discountOverride = Boolean(row.discount_override);
              const discountControlEligible = Boolean(
                onDiscount && row.automatic_discount_eligible,
              );
              const discountDisplayEligible = Boolean(
                discountControlEligible || (onDiscount && discountOverride),
              );
              const netAmount = panelNetAmount(row);
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
                  <td className="panel-title-cell">{row.title}</td>
                  <td className="amount">
                    {onNetAmountEdit ? (
                      <button
                        type="button"
                        className="amount-cell-button"
                        onClick={() => onNetAmountEdit(row)}
                      >
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
                            disabled={row.discount_policy === "disabled"}
                          />
                          <span className="net-amount">원금 {formatWon(row.amount_value)}</span>
                        </>
                      ) : discountDisplayEligible ? (
                        <>
                          <span
                            className={
                              currentDiscount > 0
                                ? "discount-badge"
                                : "discount-badge muted-discount-badge"
                            }
                          >
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
