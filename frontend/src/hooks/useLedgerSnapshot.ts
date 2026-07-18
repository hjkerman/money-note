import { useCallback } from "react";
import {
  fetchCardDiscountMonth,
  fetchCashFlows,
  fetchCurrentCardPayments,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchArchiveEntries,
  fetchConfirmedPlannedEntries,
  fetchJudgment,
  fetchLabels,
  fetchMonthCloseStatus,
  fetchSettings,
  fetchSummary,
} from "../api";
import { monthFirstDay, monthLastDay, previousMonthFirstDay } from "../utils";

export async function fetchLedgerSnapshot() {
  const monthCloseStatus = await fetchMonthCloseStatus();
  const calendarMonth = monthCloseStatus.calendar_month;
  const calendarMonthFirstDay = monthFirstDay(calendarMonth);
  const [
    entries,
    confirmedPlannedEntries,
    archiveEntries,
    panels,
    summary,
    judgment,
    labels,
    cashFlows,
    settings,
    cardPayments,
    ownerDiscountMonth,
    familyDiscountMonth,
  ] = await Promise.all([
    fetchCurrentEntries(),
    fetchConfirmedPlannedEntries(),
    fetchArchiveEntries(),
    fetchCurrentPanels(),
    fetchSummary(),
    fetchJudgment().catch(() => null),
    fetchLabels(),
    fetchCashFlows({
      dateFrom: previousMonthFirstDay(calendarMonthFirstDay),
      dateTo: monthLastDay(calendarMonth),
    }),
    fetchSettings(),
    fetchCurrentCardPayments(),
    fetchCardDiscountMonth(calendarMonth, "owner"),
    fetchCardDiscountMonth(calendarMonth, "family"),
  ]);

  return {
    entries,
    confirmedPlannedEntries,
    archiveEntries,
    panels,
    summary,
    judgment,
    labels,
    cashFlows,
    settings,
    cardPayments,
    monthCloseStatus,
    ownerDiscountMonth,
    familyDiscountMonth,
  };
}

export function useLedgerSnapshot() {
  const loadLedgerSnapshot = useCallback(() => fetchLedgerSnapshot(), []);
  return { loadLedgerSnapshot };
}
