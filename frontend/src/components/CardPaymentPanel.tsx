import { FormEvent } from "react";
import { CardDiscountPolicy, CardPaymentRow, CardPaymentStatus, JudgmentState } from "../api";
import { DiscountPolicyBar } from "./Insights";
import {
  daysBetween,
  displayEntryTitle,
  formatDateLabel,
  formatMonthLabel,
  formatWon,
  previousMonthFirstDay,
  previousMonthLastDay,
  sumPaymentAllocationInputs,
  today,
} from "../utils";

const hasOwn = (record: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(record, key);

export function CardPaymentPanel({
  status,
  fallbackLiquidity,
  availableLiquidity,
  onAcknowledgeLiquidityReset,
  allocations,
  setAllocations,
  paymentBudget,
  setPaymentBudget,
  onDiscountPolicyChange,
  onDiscountToggle,
  onAutoAllocate,
  onSelect,
  onSubmit,
  onDeleteEvent,
  onDeleteRow,
  onTollDeferral,
  paymentTone,
  lateEntryForm,
  setLateEntryForm,
  onLateEntrySubmit,
  isBusy,
}: {
  status: CardPaymentStatus | null;
  fallbackLiquidity: number;
  availableLiquidity: number;
  onAcknowledgeLiquidityReset: () => void;
  allocations: Record<string, string>;
  setAllocations: (value: Record<string, string>) => void;
  paymentBudget: string;
  setPaymentBudget: (value: string) => void;
  onDiscountPolicyChange: (policy: CardDiscountPolicy) => void;
  onDiscountToggle: (row: CardPaymentRow, exclude: boolean) => void;
  onAutoAllocate: () => void;
  onSelect: (row: CardPaymentRow, selected: boolean) => void;
  onSubmit: () => void;
  onDeleteEvent: (eventId: number) => void;
  onDeleteRow: (row: CardPaymentRow) => void;
  onTollDeferral: (row: CardPaymentRow, defer: boolean) => void;
  paymentTone: JudgmentState["payment"] | null;
  lateEntryForm: { date: string; usagePlace: string; usageItem: string; amount: string };
  setLateEntryForm: (value: { date: string; usagePlace: string; usageItem: string; amount: string }) => void;
  onLateEntrySubmit: (event: FormEvent) => Promise<void>;
  isBusy: boolean;
}) {
  if (!status) {
    return <section className="panel"><p className="empty">결제 현황을 불러오는 중입니다.</p></section>;
  }
  const referenceLiquidity = status.primary_income_total > 0 ? status.primary_income_total : fallbackLiquidity;
  const pressure = paymentTone ?? { level: "quiet", message: "결제 판단을 불러오는 중입니다." };
  const selectedTotal = sumPaymentAllocationInputs(allocations);
  return (
    <section className="payment-stack">
      <section className={`panel payment-overview ${pressure.level}`}>
        <div className="panel-header">
          <div>
            <h2>이번달 결제</h2>
            <p>{formatMonthLabel(status.usage_month)} 사용분 · {formatDateLabel(status.due_date)}까지 즉시결제 가능</p>
          </div>
          <span>{formatWon(status.effective_remaining_total)}</span>
        </div>
        {status.needs_liquidity_reset ? (
          <div className="payment-alert">
            <span>결제 안 된 내역 있습니다. 유동성 현황을 재설정하세요.</span>
            <button type="button" onClick={onAcknowledgeLiquidityReset}>유동성 보정 완료</button>
          </div>
        ) : null}
        <p className="judgment-line">{pressure.message}</p>
        <DiscountPolicyBar
          month={status.usage_month}
          scope="owner"
          status={{
            month: status.usage_month,
            scope: "owner",
            policy: status.discount_policy,
            discounts: {},
            discount_total: status.discount_total,
          }}
          onChange={(_scope, _month, policy) => onDiscountPolicyChange(policy)}
          isBusy={isBusy}
        />
        <dl className="payment-summary">
          <div><dt>심사 기준 수입</dt><dd>{formatWon(referenceLiquidity)}</dd></div>
          <div><dt>원래 결제액</dt><dd>{formatWon(status.original_total)}</dd></div>
          <div><dt>즉시결제 누적</dt><dd>{formatWon(status.immediate_paid_total)}</dd></div>
          <div><dt>할인액 누적</dt><dd>{formatWon(status.discount_total)}</dd></div>
          <div><dt>기록상 미결제</dt><dd>{formatWon(status.recorded_remaining_total)}</dd></div>
        </dl>
        <p className="fallback-note">이달 기준 수입 기록이 없으면 설정의 기본 예정 수입 {formatWon(fallbackLiquidity)}을 심사 기준으로 씁니다.</p>
        <div className="payment-controls">
          <label className="payment-budget-field">
            <input
              type="number"
              min="0"
              step="1"
              value={paymentBudget}
              onChange={(event) => setPaymentBudget(event.target.value)}
              inputMode="numeric"
              aria-label="자동 배분 한도"
              placeholder={`자동 배분 한도(기본 ${formatWon(availableLiquidity)})`}
            />
          </label>
          <button type="button" onClick={onAutoAllocate} disabled={isBusy || !status.immediate_allowed}>
            날짜순 자동 배분
          </button>
          <button type="button" onClick={() => setAllocations({})} disabled={isBusy}>선택 해제</button>
          <button
            type="button"
            className="save-needed"
            onClick={onSubmit}
            disabled={
              isBusy ||
              selectedTotal <= 0 ||
              !status.immediate_allowed
            }
          >
            즉시결제 반영 {formatWon(selectedTotal)}
          </button>
        </div>
      </section>

      <section className="panel late-entry-panel">
        <div className="panel-header">
          <div>
            <h2>전월 매입 지연 보정</h2>
            <p>카드사가 월말 뒤에 올린 직전월 사용내역을 추가합니다. 과거 기록은 삭제하지 않습니다.</p>
          </div>
          <span>{status.rows.filter((row) => row.entry_kind === "late_expense").length}건</span>
        </div>
        <form className="entry-form" onSubmit={(event) => void onLateEntrySubmit(event)}>
          <input
            type="date"
            value={lateEntryForm.date}
            min={previousMonthFirstDay(today)}
            max={previousMonthLastDay(today)}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, date: event.target.value })}
          />
          <input
            value={lateEntryForm.usagePlace}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, usagePlace: event.target.value })}
            placeholder="사용처"
          />
            <input
              value={lateEntryForm.usageItem}
              onChange={(event) => setLateEntryForm({ ...lateEntryForm, usageItem: event.target.value })}
            placeholder="세부내역"
            />
          <input
            type="number"
            min="0"
            step="1"
            value={lateEntryForm.amount}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, amount: event.target.value })}
            inputMode="numeric"
            placeholder="금액"
          />
          <button type="submit" disabled={isBusy}>추가</button>
        </form>
        {status.rows.some((row) => row.entry_kind === "late_expense") ? (
          <table>
            <thead><tr><th>날짜</th><th>세부내역</th><th className="amount">금액</th></tr></thead>
            <tbody>
              {status.rows.filter((row) => row.entry_kind === "late_expense").map((row) => (
                <tr key={row.id}>
                  <td className="date">{row.date_label}</td>
                  <td>{displayEntryTitle(row)}</td>
                  <td className="amount">{formatWon(row.amount_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="empty">카드사가 뒤늦게 제출한 전월 내역이 없습니다.</p>}
      </section>

      <section className="panel payment-ledger">
        <div className="panel-header">
          <h2>결제 대상 사용내역</h2>
          <span>{status.rows.filter((row) => !row.is_deferred && row.remaining_amount > 0).length}건</span>
        </div>
        {status.rows.length ? (
          <table>
            <thead>
              <tr>
                <th className="select-cell">선택</th>
                <th>날짜</th>
                <th>세부내역</th>
                <th className="amount">원래 금액</th>
                <th className="amount">즉시결제</th>
                <th className="amount">할인</th>
                <th className="amount">남은 금액</th>
                <th className="payment-input-cell">이번 처리액</th>
                <th className="action-cell">삭제</th>
              </tr>
            </thead>
            <tbody>
              {status.rows.map((row) => {
                const key = row.payment_key ?? "";
                const selected = Boolean(key && hasOwn(allocations, key));
                const discountExcluded = Boolean(row.discount_override && row.discount_amount <= 0);
                const discountEligible = status.discount_policy !== "disabled" && !row.is_toll;
                return (
                  <tr
                    key={row.id}
                    className={[
                      row.remaining_amount <= 0 ? "paid-row" : "",
                      row.is_deferred ? "deferred-row" : "",
                      row.is_carried_over ? "carried-row" : "",
                    ].filter(Boolean).join(" ")}
                  >
                    <td className="select-cell">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={
                          !key ||
                          row.is_deferred ||
                          row.remaining_amount <= 0 ||
                          !status.immediate_allowed
                        }
                        onChange={(event) => onSelect(row, event.target.checked)}
                      />
                    </td>
                    <td className="date">{row.is_carried_over ? "" : row.date_label ?? ""}</td>
                    <td>
                      {displayEntryTitle(row)}
                      {row.is_group ? <span className="deferred-badge">통합 {row.entry_ids.length}건</span> : null}
                      {row.is_transport ? <span className="transport-badge">교통</span> : null}
                      {row.is_toll ? <span className="toll-badge">통행료</span> : null}
                      {row.is_deferred ? <span className="deferred-badge">다음 달 이월 예정</span> : null}
                      {!row.is_carried_over && row.remaining_amount > 0 ? (
                        <button
                          type="button"
                          className="inline-action"
                          disabled={isBusy || !status.immediate_allowed}
                          onClick={() => onTollDeferral(row, !row.is_deferred)}
                        >
                          {row.is_deferred ? "이번 달에 처리" : "이월"}
                        </button>
                      ) : null}
                    </td>
                    <td className="amount">{formatWon(row.original_amount)}</td>
                    <td className="amount">{formatWon(row.immediate_paid_amount)}</td>
                    <td className="amount discount-payment-cell">
                      <span className="discount-payment-content">
                        <span>{formatWon(row.discount_amount)}</span>
                        {row.is_toll ? (
                          <span className="muted-badge">대상 아님</span>
                        ) : status.discount_policy === "disabled" ? (
                          <span className="muted-badge">혜택 없음</span>
                        ) : (
                          <button
                            type="button"
                            className={discountExcluded ? "discount-badge" : "inline-action"}
                            disabled={isBusy || !discountEligible}
                            onClick={() => onDiscountToggle(row, !discountExcluded)}
                          >
                            {discountExcluded ? "다시 적용" : "할인 제외"}
                          </button>
                        )}
                      </span>
                    </td>
                    <td className="amount">{formatWon(row.remaining_amount)}</td>
                    <td className="payment-input-cell">
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={selected ? allocations[key] : ""}
                        disabled={!selected}
                        inputMode="numeric"
                        max={row.remaining_amount}
                        onChange={(event) => setAllocations({ ...allocations, [key]: event.target.value })}
                        placeholder="금액"
                      />
                    </td>
                    <td className="action-cell">
                      <button type="button" className="danger" onClick={() => onDeleteRow(row)} disabled={isBusy}>
                        삭제
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p className="empty">직전월 카드 사용내역이 없습니다.</p>
        )}
      </section>

      <section className="panel payment-events">
        <div className="panel-header"><h2>당월 결제금액 기록</h2></div>
        {status.events.filter((event) => event.event_type === "immediate").length ? (
          <table>
            <thead><tr><th>날짜</th><th>종류</th><th className="amount">금액</th><th className="action-cell">취소</th></tr></thead>
            <tbody>
              {status.events.filter((event) => event.event_type === "immediate").map((event) => (
                <tr key={event.id}>
                  <td className="date">{formatDateLabel(event.event_date)}</td>
                  <td>즉시결제</td>
                  <td className="amount">{formatWon(event.total_amount)}</td>
                  <td className="action-cell"><button type="button" className="danger" onClick={() => onDeleteEvent(event.id)}>취소</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="empty">이번 달 즉시결제 기록이 없습니다.</p>}
      </section>
    </section>
  );
}
