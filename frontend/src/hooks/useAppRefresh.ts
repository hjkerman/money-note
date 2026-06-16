import { Dispatch, SetStateAction, useCallback, useRef, useState } from "react";
import {
  AuditLog,
  CardDiscountMonth,
  CardPaymentStatus,
  CashFlow,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  MonthCloseStatus,
  OperationStats,
  PreRestoreBackup,
  Settings,
  Summary,
} from "../api";
import { useLedgerSnapshot } from "./useLedgerSnapshot";
import { PanelType } from "../types";
import { formatIntegerSetting, isAuthRequiredError, previousMonthLastDay, today } from "../utils";

type ExpenseForm = { date: string; usagePlace: string; usageItem: string; spendingCategory: string; amount: string };
type CashFlowForm = {
  occurredOn: string;
  direction: string;
  title: string;
  amount: string;
  isPrimaryIncome: boolean;
};
type PanelForm = {
  panel_type: PanelType;
  title: string;
  spentOn: string;
  amount: string;
  dueDay: string;
};
type LateEntryForm = { date: string; usagePlace: string; usageItem: string; amount: string };

export function useAppRefresh({
  setCashFlowForm,
  setExpenseForm,
  setLateEntryForm,
  setPanelForm,
}: {
  setCashFlowForm: Dispatch<SetStateAction<CashFlowForm>>;
  setExpenseForm: Dispatch<SetStateAction<ExpenseForm>>;
  setLateEntryForm: Dispatch<SetStateAction<LateEntryForm>>;
  setPanelForm: Dispatch<SetStateAction<PanelForm>>;
}) {
  const { loadLedgerSnapshot } = useLedgerSnapshot();
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [archiveEntries, setArchiveEntries] = useState<LedgerEntry[]>([]);
  const [panels, setPanels] = useState<MonthlyPanel[]>([]);
  const [cashFlows, setCashFlows] = useState<CashFlow[]>([]);
  const [cardPayments, setCardPayments] = useState<CardPaymentStatus | null>(null);
  const [ownerDiscountMonth, setOwnerDiscountMonth] = useState<CardDiscountMonth | null>(null);
  const [familyDiscountMonth, setFamilyDiscountMonth] = useState<CardDiscountMonth | null>(null);
  const [monthCloseStatus, setMonthCloseStatus] = useState<MonthCloseStatus | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [operationStats, setOperationStats] = useState<OperationStats | null>(null);
  const [preRestoreBackups, setPreRestoreBackups] = useState<PreRestoreBackup[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [judgment, setJudgment] = useState<JudgmentState | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [settings, setSettings] = useState<Settings>({});
  const [status, setStatus] = useState("서버와 통신 준비 중");
  const [isBusy, setIsBusy] = useState(false);
  const [interestExpenseInput, setInterestExpenseInput] = useState("");
  const [scheduledIncomeInput, setScheduledIncomeInput] = useState("");
  const [cardLimitInput, setCardLimitInput] = useState("");
  const [ownerCardLast4Input, setOwnerCardLast4Input] = useState("");
  const [familyCardLast4Input, setFamilyCardLast4Input] = useState("");
  const [paymentAllocations, setPaymentAllocations] = useState<Record<string, string>>({});
  const [paymentBudget, setPaymentBudget] = useState("");
  const authRequiredHandler = useRef<() => void>(() => setStatus("로그인이 필요합니다."));

  const registerAuthRequiredHandler = useCallback((handler: () => void) => {
    authRequiredHandler.current = handler;
  }, []);

  const refresh = useCallback(async () => {
    setIsBusy(true);
    try {
      const snapshot = await loadLedgerSnapshot();
      setEntries(snapshot.entries);
      setArchiveEntries(snapshot.archiveEntries);
      setPanels(snapshot.panels);
      setSummary(snapshot.summary);
      setJudgment(snapshot.judgment);
      setLabels(snapshot.labels);
      setCashFlows(snapshot.cashFlows);
      setSettings(snapshot.settings);
      setInterestExpenseInput(formatIntegerSetting(snapshot.settings.interest_expense));
      setScheduledIncomeInput(formatIntegerSetting(snapshot.settings.base_next_month_liquidity));
      setCardLimitInput(formatIntegerSetting(snapshot.settings.card_limit));
      setOwnerCardLast4Input(snapshot.settings.owner_card_last4 ?? "");
      setFamilyCardLast4Input(snapshot.settings.family_card_last4 ?? "");
      setCardPayments(snapshot.cardPayments);
      setMonthCloseStatus(snapshot.monthCloseStatus);
      setOwnerDiscountMonth(snapshot.ownerDiscountMonth);
      setFamilyDiscountMonth(snapshot.familyDiscountMonth);
      setExpenseForm((form) => (form.date === today ? { ...form, date: snapshot.monthCloseStatus.calendar_date } : form));
      setCashFlowForm((form) =>
        form.occurredOn === today ? { ...form, occurredOn: snapshot.monthCloseStatus.calendar_date } : form,
      );
      setPanelForm((form) =>
        form.spentOn === today ? { ...form, spentOn: snapshot.monthCloseStatus.calendar_date } : form,
      );
      setLateEntryForm((form) =>
        form.date === previousMonthLastDay(today)
          ? { ...form, date: previousMonthLastDay(snapshot.monthCloseStatus.calendar_date) }
          : form,
      );
      setStatus("동기화 완료");
    } catch (error) {
      if (isAuthRequiredError(error)) {
        authRequiredHandler.current();
        return;
      }
      setStatus(`서버 통신 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }, [loadLedgerSnapshot, setCashFlowForm, setExpenseForm, setLateEntryForm, setPanelForm]);

  const clearLedgerState = useCallback(() => {
    setEntries([]);
    setArchiveEntries([]);
    setPanels([]);
    setCashFlows([]);
    setCardPayments(null);
    setSummary(null);
    setLabels({});
  }, []);

  const withRefresh = useCallback(
    async (action: () => Promise<void>) => {
      setIsBusy(true);
      try {
        await action();
        await refresh();
      } catch (error) {
        setStatus(`작업 실패: ${error instanceof Error ? error.message : String(error)}`);
        setIsBusy(false);
      }
    },
    [refresh],
  );

  return {
    archiveEntries,
    auditLogs,
    cardLimitInput,
    cardPayments,
    cashFlows,
    clearLedgerState,
    entries,
    familyCardLast4Input,
    familyDiscountMonth,
    interestExpenseInput,
    isBusy,
    judgment,
    labels,
    monthCloseStatus,
    ownerCardLast4Input,
    ownerDiscountMonth,
    operationStats,
    panels,
    paymentAllocations,
    paymentBudget,
    preRestoreBackups,
    refresh,
    registerAuthRequiredHandler,
    scheduledIncomeInput,
    setAuditLogs,
    setCardLimitInput,
    setFamilyCardLast4Input,
    setInterestExpenseInput,
    setIsBusy,
    setOwnerCardLast4Input,
    setOperationStats,
    setPaymentAllocations,
    setPaymentBudget,
    setPreRestoreBackups,
    setScheduledIncomeInput,
    setStatus,
    settings,
    status,
    summary,
    withRefresh,
  };
}
