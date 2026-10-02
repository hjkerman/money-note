import { describe, expect, it } from "vitest";
import { parseAmount } from "./utils";
import { validateMoneyPayload } from "./money";

describe("exact monetary boundary", () => {
  it("parses the safe boundary without rounding a neighbouring amount", () => {
    expect(parseAmount("9007199254740991")).toBe(Number.MAX_SAFE_INTEGER);
    expect(parseAmount("9007199254740992")).toBeNull();
    expect(parseAmount("9007199254740993")).toBeNull();
    expect(parseAmount("5000.00000000000001")).toBeNull();
    expect(parseAmount("10,000")).toBe(10000);
  });
  it("rejects unsafe monetary responses, not rates or unrelated metadata", () => {
    expect(() => validateMoneyPayload({ cash_flow_balance: Number.MAX_SAFE_INTEGER })).not.toThrow();
    expect(() => validateMoneyPayload({ current_month_spendable: 2 ** 53 })).toThrow();
    expect(() => validateMoneyPayload({ rows: [{ amount_value: 0.5 }] })).toThrow();
    expect(() => validateMoneyPayload({ rate: 0.012, amount_value: 10000 })).not.toThrow();
    for (const key of ["scheduled_income", "cash_flow_balance", "card_limit", "base_next_month_liquidity", "liquidity_status"]) {
      expect(() => validateMoneyPayload({ [key]: "9007199254740993" })).toThrow();
      expect(() => validateMoneyPayload({ key, value: "9007199254740993" })).toThrow();
      expect(() => validateMoneyPayload({ [key]: "9007199254740991" })).not.toThrow();
    }
  });
});
