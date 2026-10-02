// Transport/domain validation only. Financial calculations remain on the server.
const moneyFields = new Set([
  "amount_value", "aux_amount_value", "actual_amount", "discount_override_amount", "total_amount",
  "discount_amount", "automatic_discount_amount", "effective_discount_amount", "effective_amount_value",
  "confirmed_amount_value", "confirmed_effective_discount_amount", "confirmed_effective_amount_value",
  "original_amount", "immediate_paid_amount", "remaining_amount", "original_total", "immediate_paid_total",
  "discount_total", "recorded_remaining_total", "effective_remaining_total", "primary_income_total",
  "scheduled_income", "cash_flow_balance", "remaining_liquidity", "current_month_spendable",
  "current_spending_total", "current_discount_total", "card_total", "planned_recurring_total",
  "fixed_cash_total", "fixed_cash_processed_total", "transfer_or_deposit_total", "frozen_asset_total",
  "claim_original_total", "claim_net_total", "family_card_original_total", "family_card_net_total",
  "visible_cash_flow_total", "card_limit", "base_next_month_liquidity", "liquidity_status",
  "total", "minimum_total", "minimum_discount_total",
]);

export function parseExactMoney(value: string): number | null {
  if (!/^[+-]?\d+(?:\.0+)?$/.test(value.trim())) return null;
  const parsed = Number(value);
  return Number.isSafeInteger(parsed) ? parsed : null;
}

export function validateMoneyPayload(value: unknown): void {
  if (Array.isArray(value)) {
    value.forEach(validateMoneyPayload);
  } else if (value !== null && typeof value === "object") {
    const row = value as Record<string, unknown>;
    if (typeof row.key === "string" && moneyFields.has(row.key) && "value" in row
      && (typeof row.value !== "string" || parseExactMoney(row.value) === null)) {
      throw new Error(`금액 설정 형식이 올바르지 않습니다: ${row.key}`);
    }
    Object.entries(value).forEach(([key, child]) => {
      if (moneyFields.has(key) && child !== null) {
        const valid = typeof child === "number" ? Number.isSafeInteger(child)
          : typeof child === "string" && parseExactMoney(child) !== null;
        if (!valid) throw new Error(`금액 범위 또는 형식이 올바르지 않습니다: ${key}`);
      } else if (typeof child === "object") validateMoneyPayload(child);
    });
  }
}
