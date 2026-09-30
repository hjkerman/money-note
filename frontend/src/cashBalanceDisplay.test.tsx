import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";

import { Summary } from "./api";
import { CashFlowView, FixedPanelView } from "./components/MonthlyPanelsView";
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
  fixed_cash_processed_total: 0,
  transfer_or_deposit_total: 933_170,
  frozen_asset_total: 0,
  claim_original_total: 95_220,
  claim_net_total: 73_002,
  family_card_original_total: 0,
  family_card_net_total: 0,
  visible_cash_flow_total: 1_256_404,
};

test("cash-flow panel shows the server's full cash balance, not the visible-row subtotal", () => {
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

test("cash-flow navigation tab uses the same full server cash balance", () => {
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

test("fixed panel displays actual processed outflow over all template reserves from the server", () => {
  const html = renderToStaticMarkup(
    <FixedPanelView
      active
      currentMonth="2026-10"
      calendarDate="2026-10-01"
      handlePanelDelete={() => undefined}
      handleFixedPanelConfirm={() => undefined}
      handleFixedPanelConfirmationCancel={() => undefined}
      handlePanelSubmit={async () => undefined}
      handlePlannedConfirm={() => undefined}
      handlePlannedDelete={() => undefined}
      handlePlannedSubmit={() => undefined}
      isBusy={false}
      labels={{}}
      panelForm={{ panel_type: "fixed", title: "", spentOn: "", amount: "", dueDay: "" }}
      panels={[]}
      confirmedPlannedEntries={[]}
      plannedEntries={[]}
      plannedForm={{ dueDay: "", usagePlace: "", usageItem: "", amount: "" }}
      setPanelForm={() => undefined}
      setPlannedForm={() => undefined}
      summary={{ ...summary, fixed_cash_processed_total: 112_430, fixed_cash_total: 150_000 }}
    />,
  );

  expect(html).toContain("112,430원 / 총 150,000원");
});
