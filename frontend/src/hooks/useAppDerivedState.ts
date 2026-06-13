import { useMemo } from "react";
import { CardDiscountMonth, CardPaymentStatus, CashFlow, LedgerEntry, MonthlyPanel, MonthCloseStatus, Summary } from "../api";
import { CurrentTab, PrimaryTab } from "../types";
import {
  activeStatItems,
  collectEntryMonths,
  compareEntriesByDate,
  detectCurrentMonth,
  panelLabel,
  sumAmounts,
  sumCashFlows,
  sumPanelAmounts,
  sumPanelNetAmounts,
} from "../utils";

export function useAppDerivedState({
  archiveEntries,
  cardPayments,
  cashFlows,
  entries,
  familyDiscountMonth,
  labels,
  monthCloseStatus,
  ownerDiscountMonth,
  panels,
  selectedHistoryMonth,
  summary,
}: {
  archiveEntries: LedgerEntry[];
  cardPayments: CardPaymentStatus | null;
  cashFlows: CashFlow[];
  entries: LedgerEntry[];
  familyDiscountMonth: CardDiscountMonth | null;
  labels: Record<string, string>;
  monthCloseStatus: MonthCloseStatus | null;
  ownerDiscountMonth: CardDiscountMonth | null;
  panels: MonthlyPanel[];
  selectedHistoryMonth: string;
  summary: Summary | null;
}) {
  const plannedEntries = useMemo(() => entries.filter((entry) => entry.entry_kind === "planned"), [entries]);
  const expenseEntries = useMemo(() => entries.filter((entry) => entry.entry_kind !== "planned"), [entries]);
  const currentMonth = useMemo(
    () => monthCloseStatus?.calendar_month ?? detectCurrentMonth(entries),
    [entries, monthCloseStatus?.calendar_month],
  );
  const structuredHistoryEntries = useMemo(
    () => [...entries, ...archiveEntries].filter((entry) => entry.entry_kind !== "planned" && entry.entry_date),
    [archiveEntries, entries],
  );
  const historyMonths = useMemo(() => collectEntryMonths(structuredHistoryEntries, currentMonth), [structuredHistoryEntries, currentMonth]);
  const historyEntries = useMemo(
    () =>
      structuredHistoryEntries
        .filter((entry) => entry.entry_date?.startsWith(selectedHistoryMonth))
        .sort(compareEntriesByDate),
    [selectedHistoryMonth, structuredHistoryEntries],
  );
  const statsItems = useMemo(() => activeStatItems(historyEntries), [historyEntries]);
  const primaryTabs: { id: PrimaryTab; label: string; total: number }[] = useMemo(
    () => [
      {
        id: "current",
        label: "당월",
        total: sumAmounts(expenseEntries),
      },
      {
        id: "payment",
        label: "이번달 결제",
        total: cardPayments?.effective_remaining_total ?? 0,
      },
      {
        id: "fixed",
        label: "고정지출",
        total:
          summary?.transfer_or_deposit_total ??
          sumPanelAmounts(panels.filter((panel) => panel.panel_type === "fixed")) + sumAmounts(plannedEntries),
      },
      {
        id: "frozen",
        label: panelLabel(labels, "frozen"),
        total: sumPanelAmounts(panels.filter((panel) => panel.panel_type === "frozen")),
      },
      {
        id: "cash",
        label: "현금흐름",
        total: sumCashFlows(cashFlows),
      },
    ],
    [cardPayments?.effective_remaining_total, cashFlows, expenseEntries, labels, panels, plannedEntries, summary?.transfer_or_deposit_total],
  );
  const currentSubTabs: { id: CurrentTab; label: string; total: number }[] = useMemo(
    () => [
      { id: "expenses", label: "당월 지출", total: sumAmounts(expenseEntries) },
      {
        id: "claim",
        label: panelLabel(labels, "claim"),
        total: sumPanelNetAmounts(
          panels.filter((panel) => panel.panel_type === "claim"),
          ownerDiscountMonth?.policy,
        ),
      },
      {
        id: "family_card",
        label: panelLabel(labels, "family_card"),
        total: sumPanelNetAmounts(
          panels.filter((panel) => panel.panel_type === "family_card"),
          familyDiscountMonth?.policy,
        ),
      },
    ],
    [expenseEntries, familyDiscountMonth?.policy, labels, ownerDiscountMonth?.policy, panels],
  );

  return {
    currentMonth,
    currentSubTabs,
    expenseEntries,
    historyEntries,
    historyMonths,
    plannedEntries,
    primaryTabs,
    statsItems,
  };
}
