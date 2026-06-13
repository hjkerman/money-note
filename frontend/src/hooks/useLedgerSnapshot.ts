import { useCallback } from "react";
import {
  fetchCardDiscountMonth,
  fetchCashFlows,
  fetchCurrentCardPayments,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchArchiveEntries,
  fetchJudgment,
  fetchLabels,
  fetchMonthCloseStatus,
  fetchSettings,
  fetchSummary,
} from "../api";

export async function fetchLedgerSnapshot() {
  const monthCloseStatus = await fetchMonthCloseStatus();
  const calendarMonth = monthCloseStatus.calendar_month;
  const [
    entries,
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
    fetchArchiveEntries(),
    fetchCurrentPanels(),
    fetchSummary(),
    fetchJudgment().catch(() => null),
    fetchLabels(),
    fetchCashFlows(),
    fetchSettings(),
    fetchCurrentCardPayments(),
    fetchCardDiscountMonth(calendarMonth, "owner"),
    fetchCardDiscountMonth(calendarMonth, "family"),
  ]);

  return {
    entries,
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
