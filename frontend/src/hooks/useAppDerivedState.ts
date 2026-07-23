import { useMemo } from "react";
import { CardPaymentStatus, LedgerEntry, MonthCloseStatus, Summary } from "../api";
import { CurrentTab, PrimaryTab } from "../types";
import {
  activeStatItems,
  collectEntryMonths,
  compareEntriesByDate,
  detectCurrentMonth,
  panelLabel,
} from "../utils";

export function useAppDerivedState({
  archiveEntries,
  cardPayments,
  entries,
  labels,
  monthCloseStatus,
  selectedHistoryMonth,
  summary,
}: {
  archiveEntries: LedgerEntry[];
  cardPayments: CardPaymentStatus | null;
  entries: LedgerEntry[];
  labels: Record<string, string>;
  monthCloseStatus: MonthCloseStatus | null;
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
        total: summary?.current_spending_total ?? 0,
      },
      {
        id: "payment",
        label: "이번달 결제",
        total: cardPayments?.effective_remaining_total ?? 0,
      },
      {
        id: "fixed",
        label: "고정지출",
        total: summary?.transfer_or_deposit_total ?? 0,
      },
      {
        id: "frozen",
        label: panelLabel(labels, "frozen"),
        total: summary?.frozen_asset_total ?? 0,
      },
      {
        id: "cash",
        label: "현금흐름",
        total: summary?.visible_cash_flow_total ?? 0,
      },
    ],
    [
      cardPayments?.effective_remaining_total,
      labels,
      summary?.current_spending_total,
      summary?.frozen_asset_total,
      summary?.transfer_or_deposit_total,
      summary?.visible_cash_flow_total,
    ],
  );
  const currentSubTabs: { id: CurrentTab; label: string; total: number }[] = useMemo(
    () => [
      { id: "expenses", label: "당월 지출", total: summary?.current_spending_total ?? 0 },
      {
        id: "claim",
        label: panelLabel(labels, "claim"),
        total: summary?.claim_net_total ?? 0,
      },
      {
        id: "family_card",
        label: panelLabel(labels, "family_card"),
        total: summary?.family_card_net_total ?? 0,
      },
    ],
    [labels, summary?.claim_net_total, summary?.current_spending_total, summary?.family_card_net_total],
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
