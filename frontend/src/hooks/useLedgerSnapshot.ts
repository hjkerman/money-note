import { useCallback } from "react";
import {
  fetchCardDiscountMonth,
  fetchCashFlows,
  fetchCurrentCardPayments,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchArchiveEntries,
  fetchInstallments,
  fetchJudgment,
  fetchLabels,
  fetchMonthCloseStatus,
  fetchSettings,
  fetchSummary,
} from "../api";
import { today } from "../utils";

export async function fetchLedgerSnapshot() {
  const [
    entries,
    archiveEntries,
    panels,
    summary,
    judgment,
    labels,
    cashFlows,
    settings,
    installments,
    cardPayments,
    monthCloseStatus,
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
    fetchInstallments(),
    fetchCurrentCardPayments(),
    fetchMonthCloseStatus(),
    fetchCardDiscountMonth(today.slice(0, 7), "owner"),
    fetchCardDiscountMonth(today.slice(0, 7), "family"),
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
    installments,
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
