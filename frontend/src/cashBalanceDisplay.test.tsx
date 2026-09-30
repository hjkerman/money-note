import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";

import { Summary } from "./api";
import { CashFlowView } from "./components/MonthlyPanelsView";
import { useAppDerivedState } from "./hooks/useAppDerivedState";

const summary: Summary = {
  scheduled_income: 1_459_200,
  cash_flow_balance: 1_756_404,
  remaining_liquidity: 1_328_846,
  current_spending_total: 0,
  current_discount_total: 0,
  card_total: 0,
  planned_recurring_total: 113_170,
  fixed_cash_total: 820_000,
  transfer_or_deposit_total: 933_170,
  frozen_asset_total: 0,
  claim_original_total: 95_220,
  claim_net_total: 73_002,
  family_card_original_total: 0,
  family_card_net_total: 0,
  visible_cash_flow_total: 1_256_404,
};

test("cash-flow panel shows the full server cash balance rather than the visible-row subtotal", () => {
  const html = renderToStaticMarkup(
    <CashFlowView
      active
      cashFlowForm={{ occurredOn: "2026-10-01", direction: "in", title: "", amount: "", isPrimaryIncome: false }}
      cashFlows={[]}
      handleCashFlowDelete={() => undefined}
      handleCashFlowSubmit={async () => undefined}
      isBusy={false}
      onOpenHistory={() => undefined}
      setCashFlowForm={() => undefined}
      summary={summary}
    />,
  );

  expect(html).toContain("전체 잔액");
  expect(html).toContain("1,756,404원");
  expect(html).not.toContain("1,256,404원");
});

test("cash-flow tab shows the same full server cash balance", () => {
  function TabProbe() {
    const { primaryTabs } = useAppDerivedState({
      archiveEntries: [],
      cardPayments: null,
      entries: [],
      labels: {},
      monthCloseStatus: null,
      selectedHistoryMonth: "2026-10",
      summary,
    });
    return <span>{primaryTabs.find((tab) => tab.id === "cash")?.total}</span>;
  }

  expect(renderToStaticMarkup(<TabProbe />)).toContain("1756404");
});
