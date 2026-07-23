import { describe, expect, it } from "vitest";

import { LedgerEntry, MonthlyPanel } from "./api";
import {
  compareEntriesByDate,
  effectiveEntryDiscount,
  effectivePanelDiscount,
  ledgerEntriesMarkdown,
  panelNetAmount,
} from "./utils";

function entry(overrides: Partial<LedgerEntry> = {}): LedgerEntry {
  return {
    id: 1,
    book_section: "current",
    entry_kind: "expense",
    entry_date: "2026-07-01",
    date_label: null,
    group_label: null,
    title: "",
    usage_place: "사용처",
    usage_item: "세부내역",
    amount_value: 10_000,
    amount_expr: null,
    aux_amount_value: null,
    aux_amount_expr: null,
    extra_value: null,
    sort_order: 1,
    due_day: null,
    confirmed_at: null,
    confirmed_month: null,
    spending_category: null,
    payment_key: "payment-key",
    discount_override: 0,
    discount_policy: "enabled",
    automatic_discount_eligible: true,
    automatic_discount_amount: 120,
    effective_discount_amount: 120,
    effective_amount_value: 9_880,
    is_transport: false,
    is_toll: false,
    ...overrides,
  };
}

function panel(overrides: Partial<MonthlyPanel> = {}): MonthlyPanel {
  return {
    id: 1,
    month: "2026-07",
    panel_type: "claim",
    title: "생활비",
    spent_on: "2026-07-01",
    amount_value: 10_000,
    discount_amount: 0,
    discount_override: 0,
    amount_expr: null,
    sort_order: 1,
    due_day: null,
    confirmed_at: null,
    discount_policy: "enabled",
    automatic_discount_eligible: true,
    automatic_discount_amount: 120,
    effective_discount_amount: 120,
    effective_amount_value: 9_880,
    ...overrides,
  };
}

describe("웹 원장 정렬", () => {
  it("날짜가 같으면 먼저 등록한 sort_order와 id를 먼저 둔다", () => {
    const rows = [
      entry({ id: 3, sort_order: 2 }),
      entry({ id: 2, sort_order: 1 }),
      entry({ id: 1, sort_order: 1 }),
    ].sort(compareEntriesByDate);

    expect(rows.map((row) => row.id)).toEqual([1, 2, 3]);
  });
});

describe("할인과 실결제액", () => {
  it("서버가 계산한 원장 할인액을 그대로 사용한다", () => {
    expect(effectiveEntryDiscount(entry({ effective_discount_amount: 0 }))).toBe(0);
  });

  it("서버가 계산한 수동 실결제액 override를 그대로 사용한다", () => {
    expect(
      effectiveEntryDiscount(
        entry({
          effective_discount_amount: 1_200,
          effective_amount_value: 8_800,
        }),
      ),
    ).toBe(1_200);
  });

  it("서버가 계산한 청구 할인과 실결제액을 합계에 사용한다", () => {
    const row = panel({ effective_discount_amount: 2_500, effective_amount_value: 7_500 });
    expect(effectivePanelDiscount(row)).toBe(2_500);
    expect(panelNetAmount(row)).toBe(7_500);
  });
});

describe("Markdown 원장", () => {
  it("테이블 구분 문자와 줄바꿈을 안전하게 이스케이프한다", () => {
    const markdown = ledgerEntriesMarkdown(
      [entry({ usage_place: "가게|지점", usage_item: "첫 줄\n둘째 줄" })],
      "2026-07",
    );

    expect(markdown).toContain("가게\\|지점");
    expect(markdown).toContain("첫 줄 둘째 줄");
  });
});
