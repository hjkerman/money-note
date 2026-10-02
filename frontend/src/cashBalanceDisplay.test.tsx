import { renderToStaticMarkup } from "react-dom/server";
import { expect, test } from "vitest";

import { Summary } from "./api";
import { CashFlowView, FixedPanelView } from "./components/MonthlyPanelsView";
import { SummaryPanel } from "./components/Insights";
import { useAppDerivedState } from "./hooks/useAppDerivedState";
import { PanelTable } from "./components/ledger/PanelTable";
import { PlannedTable } from "./components/ledger/PlannedTable";
import { MonthlyPanel, LedgerEntry } from "./api";
import confirmedActual from "../../backend/tests/fixtures/confirmed_recurring_actual.json";

test("confirmed recurring renders the actual server amount even without occurrence date", () => {
  const html = renderToStaticMarkup(<FixedPanelView active currentMonth="2026-06"
    calendarDate="2026-06-11" handlePanelDelete={() => undefined}
    handleFixedPanelConfirm={() => undefined} handleFixedPanelConfirmationCancel={() => undefined}
    handlePanelSubmit={async () => undefined} handlePlannedConfirm={() => undefined}
    handlePlannedDelete={() => undefined} handlePlannedSubmit={() => undefined}
    isBusy={false} labels={{}} panelForm={{ panel_type: "fixed", title: "", spentOn: "", amount: "", dueDay: "" }}
    panels={[]} confirmedPlannedEntries={[{ ...confirmedActual, id: 1 } as LedgerEntry]}
    plannedEntries={[]} plannedForm={{ dueDay: "", usagePlace: "", usageItem: "", amount: "" }}
    setPanelForm={() => undefined} setPlannedForm={() => undefined} summary={summary}
  />);
  expect(html).toContain("7,000원");
  expect(html).toContain("84원");
  expect(html).toContain("6,916원");
  expect(html).not.toContain("5,000원");
});

test("cash/card confirmation controls respect server eligibility independently", () => {
  const fixed = {
    id: 1, month: "2026-10", panel_type: "fixed", title: "October transfer",
    amount_value: 820000, can_confirm_fixed: false,
  } as MonthlyPanel;
  const renderCash = (allowed: boolean) => renderToStaticMarkup(<PanelTable
    title="fixed" rows={[{ ...fixed, can_confirm_fixed: allowed }]}
    fixedConfirmationDate="2026-09-30" onConfirmFixed={() => undefined}
  />);
  expect(renderCash(false)).toMatch(/<button[^>]*disabled=""[^>]*>확인<\/button>/);
  expect(renderCash(true)).not.toMatch(/<button[^>]*disabled=""[^>]*>확인<\/button>/);
  const card = { id: 2, title: "recurring", amount_value: 1000, due_day: 1 } as LedgerEntry;
  const html = renderToStaticMarkup(<PlannedTable entries={[card]} month="2026-09"
    emptyText="empty" canConfirm={false} onConfirm={() => undefined} onDelete={() => undefined}
  />);
  expect(html).toMatch(/<button[^>]*disabled=""[^>]*>확인<\/button>/);
});

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

test("the remaining-liquidity slot renders the server's current-month spendable value", () => {
  const html = renderToStaticMarkup(
    <SummaryPanel
      summary={{ ...summary, remaining_liquidity: 1_261_930, current_month_spendable: 441_930 }}
      judgment={null}
      labels={{}}
    />,
  );

  expect(html).toContain("441,930원");
  expect(html).not.toContain("1,261,930원");
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
