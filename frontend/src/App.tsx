import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import {
  AuthUser,
  AuditLog,
  CardDiscountMonth,
  CardDiscountPolicy,
  CardPaymentRow,
  CardPaymentStatus,
  CashFlow,
  Installment,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  MonthCloseStatus,
  Settings,
  SpendingCategory,
  Summary,
  acknowledgeLiquidityReset,
  appendPlannedEntry,
  cancelTollDeferral,
  changePassword,
  clearAuditLogs,
  clearEntryDiscount,
  clearPanelDiscount,
  closeCurrentMonth,
  completePanelsByType,
  confirmPlannedEntry,
  createCashFlow,
  createCardPaymentEvent,
  createEntry,
  createInstallment,
  createLateCardEntry,
  createPanel,
  deleteEntry,
  deleteCashFlow,
  deleteCardPaymentEvent,
  deleteInstallment,
  deletePanel,
  deletePlannedEntry,
  deferTollPayment,
  fetchAuditLogs,
  fetchMe,
  downloadCsvBackup,
  importCsvBackup,
  login,
  logout,
  resetLedgerData,
  setSharePin,
  sharePageUrl,
  updateEntry,
  updateCardDiscountPolicy,
  updateEntryDiscount,
  updatePanelDiscount,
  updateSetting,
} from "./api";
import { useLedgerSnapshot } from "./hooks/useLedgerSnapshot";
import { CurrentTab, PanelType, PrimaryTab } from "./types";
import {
  AuditLogPanel,
  CreditUsagePanel,
  DiscountPolicyBar,
  SummaryPanel,
} from "./components/Insights";
import { StatsModal } from "./components/StatsModal";
import { CardPaymentPanel } from "./components/CardPaymentPanel";
import {
  CashFlowPanel,
  EntryTable,
  InstallmentTable,
  PanelAppendForm,
  PanelTable,
  PlannedTable,
} from "./components/LedgerTables";
import {
  activeStatItems,
  collectEntryMonths,
  compareEntriesByDate,
  currentTabs,
  detectCurrentMonth,
  displayEntryTitle,
  focusFirstDataInput,
  formatDateLabel,
  formatIntegerSetting,
  formatMonthLabel,
  formatUsageTitle,
  formatWon,
  isAuthRequiredError,
  nextSortOrder,
  panelLabel,
  parseAmount,
  parseOptionalDay,
  parseSettingNumber,
  previousMonthLastDay,
  sumAmounts,
  sumCashFlows,
  sumInstallmentMonthlyAmounts,
  sumPanelAmounts,
  sumPanelNetAmounts,
  sumPaymentAllocationInputs,
  today,
} from "./utils";

export function App() {
  const { loadLedgerSnapshot } = useLedgerSnapshot();
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [archiveEntries, setArchiveEntries] = useState<LedgerEntry[]>([]);
  const [panels, setPanels] = useState<MonthlyPanel[]>([]);
  const [cashFlows, setCashFlows] = useState<CashFlow[]>([]);
  const [installments, setInstallments] = useState<Installment[]>([]);
  const [cardPayments, setCardPayments] = useState<CardPaymentStatus | null>(null);
  const [ownerDiscountMonth, setOwnerDiscountMonth] = useState<CardDiscountMonth | null>(null);
  const [familyDiscountMonth, setFamilyDiscountMonth] = useState<CardDiscountMonth | null>(null);
  const [monthCloseStatus, setMonthCloseStatus] = useState<MonthCloseStatus | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [judgment, setJudgment] = useState<JudgmentState | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [settings, setSettings] = useState<Settings>({});
  const [status, setStatus] = useState("서버와 통신 준비 중");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [expenseForm, setExpenseForm] = useState({ date: today, usagePlace: "", usageItem: "", amount: "" });
  const [plannedForm, setPlannedForm] = useState({ dueDay: "", usagePlace: "", usageItem: "", amount: "" });
  const [cashFlowForm, setCashFlowForm] = useState({
    occurredOn: today,
    direction: "in",
    title: "",
    amount: "",
    isPrimaryIncome: false,
  });
  const [installmentForm, setInstallmentForm] = useState({
    title: "",
    principal: "",
    fee: "0",
    months: "",
  });
  const [panelForm, setPanelForm] = useState<{
    panel_type: PanelType;
    title: string;
    spentOn: string;
    amount: string;
    dueDay: string;
  }>({ panel_type: "fixed", title: "", spentOn: today, amount: "", dueDay: "" });
  const [activePrimaryTab, setActivePrimaryTab] = useState<PrimaryTab>("current");
  const [activeCurrentTab, setActiveCurrentTab] = useState<CurrentTab>("expenses");
  const [selectedHistoryMonth, setSelectedHistoryMonth] = useState(today.slice(0, 7));
  const [showStats, setShowStats] = useState(false);
  const [showAuditLogs, setShowAuditLogs] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [interestExpenseInput, setInterestExpenseInput] = useState("");
  const [scheduledIncomeInput, setScheduledIncomeInput] = useState("");
  const [passwordForm, setPasswordForm] = useState({ currentPassword: "", newPassword: "" });
  const [resetPassword, setResetPassword] = useState("");
  const [paymentAllocations, setPaymentAllocations] = useState<Record<string, string>>({});
  const [paymentBudget, setPaymentBudget] = useState("");
  const [lateEntryForm, setLateEntryForm] = useState({
    date: previousMonthLastDay(today),
    usagePlace: "",
    usageItem: "",
    amount: "",
  });
  const csvBackupInputRef = useRef<HTMLInputElement | null>(null);

  const plannedEntries = entries.filter((entry) => entry.entry_kind === "planned");
  const expenseEntries = entries.filter((entry) => entry.entry_kind !== "planned");
  const currentMonth = useMemo(() => detectCurrentMonth(entries), [entries]);
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
  const statsItems = useMemo(
    () => activeStatItems(
      activePrimaryTab,
      activeCurrentTab,
      expenseEntries,
      historyEntries,
      panels,
      judgment,
      ownerDiscountMonth?.policy,
    ),
    [activeCurrentTab, activePrimaryTab, expenseEntries, historyEntries, panels, judgment, ownerDiscountMonth?.policy],
  );
  const primaryTabs: { id: PrimaryTab; label: string; total: number }[] = [
    {
      id: "current",
      label: "당월",
      total:
        sumAmounts(expenseEntries) +
        sumInstallmentMonthlyAmounts(installments),
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
        sumPanelAmounts(panels.filter((panel) => panel.panel_type === "fixed")) +
        sumAmounts(plannedEntries),
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
  ];
  const currentSubTabs: { id: CurrentTab; label: string; total: number }[] = [
    { id: "expenses", label: "당월 지출", total: sumAmounts(expenseEntries) },
    {
      id: "claim",
      label: panelLabel(labels, "claim"),
      total: sumPanelNetAmounts(panels.filter((panel) => panel.panel_type === "claim"), ownerDiscountMonth?.policy),
    },
    {
      id: "settlement",
      label: panelLabel(labels, "settlement"),
      total: sumPanelAmounts(panels.filter((panel) => panel.panel_type === "settlement")),
    },
    {
      id: "installments",
      label: "할부",
      total: sumInstallmentMonthlyAmounts(installments),
    },
  ];

  // 서버의 최신 장부 상태를 한 번에 다시 읽어 화면 상태를 갱신한다.
  async function refresh() {
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
      setInstallments(snapshot.installments);
      setCardPayments(snapshot.cardPayments);
      setMonthCloseStatus(snapshot.monthCloseStatus);
      setOwnerDiscountMonth(snapshot.ownerDiscountMonth);
      setFamilyDiscountMonth(snapshot.familyDiscountMonth);
      setStatus("동기화 완료");
    } catch (error) {
      if (isAuthRequiredError(error)) {
        setAuthUser(null);
        setStatus("로그인이 필요합니다.");
        return;
      }
      setStatus(`서버 통신 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  useEffect(() => {
    void checkAuth();
  }, []);

  useEffect(() => {
    if (!showStats) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowStats(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [showStats]);

  async function checkAuth() {
    setIsBusy(true);
    try {
      const user = await fetchMe();
      setAuthUser(user);
      await refresh();
    } catch (error) {
      if (!isAuthRequiredError(error)) {
        setStatus(`서버 통신 실패: ${error instanceof Error ? error.message : String(error)}`);
      } else {
        setStatus("로그인이 필요합니다.");
      }
    } finally {
      setAuthChecked(true);
      setIsBusy(false);
    }
  }

  async function handleLogin(event: FormEvent) {
    event.preventDefault();
    if (!loginForm.username.trim() || !loginForm.password) return;
    setIsBusy(true);
    try {
      const user = await login({
        username: loginForm.username.trim(),
        password: loginForm.password,
      });
      setAuthUser(user);
      setLoginForm({ username: "", password: "" });
      setStatus(
        user.share_pin_needs_change
          ? "로그인 완료. 가족 공유 PIN이 기본값 0000입니다. 지금 변경하세요."
          : "로그인 완료",
      );
      await refresh();
    } catch (error) {
      setStatus(`로그인 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setAuthChecked(true);
      setIsBusy(false);
    }
  }

  async function handleLogout() {
    setIsBusy(true);
    try {
      await logout();
      setAuthUser(null);
      setEntries([]);
      setArchiveEntries([]);
      setPanels([]);
      setCashFlows([]);
      setCardPayments(null);
      setSummary(null);
      setLabels({});
      setStatus("로그아웃 완료");
    } catch (error) {
      setStatus(`로그아웃 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  // 사용처와 세부내역을 합쳐 사람이 읽기 쉬운 대표 제목도 함께 저장한다.
  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const usagePlace = expenseForm.usagePlace.trim();
    const usageItem = expenseForm.usageItem.trim();
    const amount = parseAmount(expenseForm.amount);
    if (!expenseForm.date || !usagePlace || amount === null) {
      setStatus("날짜, 사용처, 금액은 필수입니다.");
      return;
    }
    await withRefresh(async () => {
      const dateLabel = formatDateLabel(expenseForm.date);
      const title = formatUsageTitle(usagePlace, usageItem);
      const created = await createEntry({
        book_section: "current",
        entry_kind: "expense",
        entry_date: expenseForm.date || null,
        date_label: dateLabel,
        group_label: null,
        title,
        usage_place: usagePlace || null,
        usage_item: usageItem || null,
        amount_value: amount,
        amount_expr: null,
        aux_amount_value: null,
        aux_amount_expr: null,
        extra_value: null,
        sort_order: nextSortOrder(entries),
        due_day: null,
        confirmed_at: null,
        spending_category: null,
        discount_override: 0,
      });
      setExpenseForm({ date: expenseForm.date, usagePlace: "", usageItem: "", amount: "" });
      setStatus(created.book_section === "archive" ? "이미 마감한 달의 전체 기록에 추가 완료" : "당월 기록 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handlePlannedSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const usagePlace = plannedForm.usagePlace.trim();
    const usageItem = plannedForm.usageItem.trim();
    const amount = parseAmount(plannedForm.amount);
    const dueDay = parseOptionalDay(plannedForm.dueDay);
    if (!usagePlace || amount === null || dueDay === null) {
      setStatus("결제일, 사용처, 금액은 필수입니다.");
      return;
    }
    await withRefresh(async () => {
      await appendPlannedEntry({
        title: formatUsageTitle(usagePlace, usageItem),
        usage_place: usagePlace || null,
        usage_item: usageItem || null,
        amount_value: amount,
        due_day: dueDay,
      });
      setPlannedForm({ dueDay: "", usagePlace: "", usageItem: "", amount: "" });
      setStatus("카드 정기결제 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handlePanelSubmit(event: FormEvent, panelType = panelForm.panel_type) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!panelForm.title.trim()) return;
    await withRefresh(async () => {
      const sameTypePanels = panels.filter((panel) => panel.panel_type === panelType);
      await createPanel({
        month: monthCloseStatus?.calendar_month ?? today.slice(0, 7),
        panel_type: panelType,
        title: panelForm.title.trim(),
        spent_on: panelType === "claim" || panelType === "settlement" ? panelForm.spentOn : null,
        amount_value: parseAmount(panelForm.amount),
        discount_amount: 0,
        amount_expr: null,
        sort_order: nextSortOrder(sameTypePanels),
        due_day: null,
        confirmed_at: null,
        discount_override: 0,
      });
      setPanelForm({ panel_type: panelType, title: "", spentOn: panelForm.spentOn, amount: "", dueDay: "" });
      setStatus(`${panelLabel(labels, panelType)} 항목 추가 완료`);
      focusFirstDataInput(form);
    });
  }

  async function handlePlannedConfirm(entry: LedgerEntry) {
    const dueText = entry.due_day ? `${entry.due_day}일` : "오늘";
    const confirmed = window.confirm(`${entry.title}을 ${dueText} 카드 결제 건으로 당월 지출에 넣을까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await confirmPlannedEntry(entry.id);
      setStatus(`${entry.title} 확인 완료`);
    });
  }

  async function handlePlannedDelete(entry: LedgerEntry) {
    const confirmed = window.confirm(`${displayEntryTitle(entry)} 카드 정기결제 항목을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePlannedEntry(entry.id);
      setStatus("카드 정기결제 삭제 완료");
    });
  }

  // 분류 변경은 즉시 서버에 저장한다.
  async function handleCategoryChange(entry: LedgerEntry, category: SpendingCategory | null) {
    if (category === entry.spending_category) return;
    await withRefresh(async () => {
      await updateEntry(entry.id, { spending_category: category });
      setStatus("분류 저장 완료");
    });
  }

  async function handleEntryDelete(entry: LedgerEntry) {
    const confirmed = window.confirm(`${entry.title} 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteEntry(entry.id);
      setStatus(entry.book_section === "archive" ? "전월 기록 삭제 완료" : "당월 기록 삭제 완료");
    });
  }

  async function handlePanelDelete(panel: MonthlyPanel) {
    const confirmed = window.confirm(`${panel.title} 항목을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePanel(panel.id);
      setStatus(`${panelLabel(labels, panel.panel_type)} 항목 삭제 완료`);
    });
  }

  async function handlePanelComplete(panelType: "claim" | "settlement") {
    const targetPanels = panels.filter((panel) => panel.panel_type === panelType);
    if (!targetPanels.length) return;
    const confirmed = window.confirm(
      `${panelLabel(labels, panelType)} 항목 ${targetPanels.length}개를 일괄 처리 완료할까요?\n\n현재 목록과 공유 페이지에서 삭제됩니다.`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await completePanelsByType(panelType);
      setStatus(`${panelLabel(labels, panelType)} ${result.completed}개 처리 완료`);
    });
  }

  async function handlePanelShare(panelType: "claim" | "settlement") {
    const url = sharePageUrl(panelType);
    try {
      await navigator.clipboard.writeText(url);
      setStatus(`${panelLabel(labels, panelType)} 공유 링크 복사 완료`);
    } catch {
      window.prompt("공유 링크를 복사하세요.", url);
      setStatus(`${panelLabel(labels, panelType)} 공유 링크 표시 완료`);
    }
  }

  async function handleCashFlowSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!cashFlowForm.title.trim()) return;
    const parsed = parseAmount(cashFlowForm.amount);
    if (parsed === null) return;
    await withRefresh(async () => {
      await createCashFlow({
        occurred_on: cashFlowForm.occurredOn,
        title: cashFlowForm.title.trim(),
        amount_value: cashFlowForm.direction === "out" ? -Math.abs(parsed) : Math.abs(parsed),
        sort_order: nextSortOrder(cashFlows),
        is_primary_income: cashFlowForm.direction === "in" && cashFlowForm.isPrimaryIncome ? 1 : 0,
      });
      setCashFlowForm({ ...cashFlowForm, title: "", amount: "" });
      setStatus("현금흐름 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleCashFlowDelete(flow: CashFlow) {
    const confirmed = window.confirm(`${flow.title} 현금흐름 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteCashFlow(flow.id);
      setStatus("현금흐름 삭제 완료");
    });
  }

  async function handleInstallmentSubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    if (!installmentForm.title.trim()) return;
    const principal = parseAmount(installmentForm.principal);
    const feeRate = Number(installmentForm.fee.replaceAll(",", "").trim() || 0);
    const months = Number(installmentForm.months);
    if (principal === null || !Number.isFinite(feeRate) || !Number.isInteger(months) || months < 1) return;
    await withRefresh(async () => {
      await createInstallment({
        title: installmentForm.title.trim(),
        principal_amount: principal,
        fee_rate: feeRate,
        months,
        remaining_months: months,
        start_month: currentMonth,
        sort_order: nextSortOrder(installments),
      });
      setInstallmentForm({ title: "", principal: "", fee: "0", months: "" });
      setStatus("할부 항목 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleInstallmentDelete(installment: Installment) {
    const confirmed = window.confirm(`${installment.title} 할부 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteInstallment(installment.id);
      setStatus("할부 항목 삭제 완료");
    });
  }

  // 날짜순으로 즉시결제 가능액을 자동 배분하고, 마지막 항목은 일부 결제로 남긴다.
  function handleAutoAllocate() {
    if (!cardPayments?.immediate_allowed) return;
    let remainingBudget = Math.max(0, parseAmount(paymentBudget) ?? summary?.liquidity_status ?? 0);
    const next: Record<string, string> = {};
    for (const row of cardPayments.rows) {
      if (!row.payment_key || row.is_deferred || row.remaining_amount <= 0 || remainingBudget <= 0) continue;
      const allocated = Math.min(row.remaining_amount, remainingBudget);
      next[row.payment_key] = String(Math.round(allocated));
      remainingBudget -= allocated;
    }
    setPaymentAllocations(next);
    setStatus(`날짜순 결제안 생성 완료: ${formatWon(sumPaymentAllocationInputs(next))}`);
  }

  function handlePaymentSelection(row: CardPaymentRow, selected: boolean) {
    if (!row.payment_key) return;
    setPaymentAllocations((current) => {
      const next = { ...current };
      if (selected) next[row.payment_key as string] = String(Math.round(row.remaining_amount));
      else delete next[row.payment_key as string];
      return next;
    });
  }

  async function handleCardPaymentSubmit() {
    if (!cardPayments?.immediate_allowed) return;
    const allocations = Object.entries(paymentAllocations)
      .flatMap(([payment_key, amountText]) => expandCardPaymentAllocation(payment_key, parseAmount(amountText) ?? 0))
      .filter((allocation) => allocation.amount_value > 0);
    if (!allocations.length) return;
    const total = allocations.reduce((sum, allocation) => sum + allocation.amount_value, 0);
    const confirmed = window.confirm(`즉시결제 ${formatWon(total)}을 선택한 사용내역에 반영할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await createCardPaymentEvent({
        event_date: today,
        event_type: "immediate",
        note: "",
        allocations,
      });
      setPaymentAllocations({});
      setStatus("즉시결제 반영 완료");
    });
  }

  async function handleCardPaymentEventDelete(eventId: number) {
    const confirmed = window.confirm("이 결제 또는 할인 기록을 취소할까요?");
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteCardPaymentEvent(eventId);
      setStatus("결제 기록 취소 완료");
    });
  }

  function expandCardPaymentAllocation(paymentKey: string, amount: number) {
    const row = cardPayments?.rows.find((item) => item.payment_key === paymentKey);
    if (!row) return [{ entry_payment_key: paymentKey, amount_value: amount }];
    let remaining = amount;
    const allocations = [];
    for (const part of row.payment_parts ?? []) {
      if (remaining <= 0) break;
      const allocated = Math.min(part.remaining_amount, remaining);
      allocations.push({ entry_payment_key: part.entry_payment_key, amount_value: allocated });
      remaining -= allocated;
    }
    return allocations;
  }

  async function handleDiscountPolicyChange(scope: "owner" | "family", month: string, policy: CardDiscountPolicy) {
    await withRefresh(async () => {
      await updateCardDiscountPolicy(month, scope, policy);
      setStatus(`${formatMonthLabel(month)} ${scope === "family" ? "가족카드" : "본인회원 카드"} 할인 혜택 설정 완료`);
    });
  }

  async function handleCurrentEntryDiscount(entry: LedgerEntry) {
    if (!entry.payment_key) return;
    if (ownerDiscountMonth?.policy === "disabled") {
      setStatus("이번 달은 본인회원 카드 할인 혜택이 없는 달로 설정되어 있습니다.");
      return;
    }
    await withRefresh(async () => {
      await updateEntryDiscount(entry.payment_key as string, 0);
      setStatus("당월 사용내역 할인 제외 완료");
    });
  }

  async function handleCurrentEntryDiscountClear(entry: LedgerEntry) {
    if (!entry.payment_key) return;
    await withRefresh(async () => {
      await clearEntryDiscount(entry.payment_key as string);
      setStatus("당월 사용내역 할인 적용 완료");
    });
  }

  async function handlePanelDiscount(panel: MonthlyPanel) {
    const isSettlement = panel.panel_type === "settlement";
    const policy = isSettlement ? familyDiscountMonth?.policy : ownerDiscountMonth?.policy;
    if (policy === "disabled") {
      setStatus(`이번 달은 ${isSettlement ? "가족카드" : "본인회원 카드"} 할인 혜택이 없는 달로 설정되어 있습니다.`);
      return;
    }
    await withRefresh(async () => {
      await updatePanelDiscount(panel.id, 0);
      setStatus(`${isSettlement ? "타인정산" : "청구"} 항목 할인 제외 완료`);
    });
  }

  async function handlePanelDiscountClear(panel: MonthlyPanel) {
    await withRefresh(async () => {
      await clearPanelDiscount(panel.id);
      setStatus(`${panel.panel_type === "settlement" ? "타인정산" : "청구"} 항목 할인 적용 완료`);
    });
  }

  async function handleTollDeferral(row: CardPaymentRow, defer: boolean) {
    if (!row.payment_keys.length) return;
    const confirmed = window.confirm(
      defer
        ? `${displayEntryTitle(row)} 항목을 다음 달 결제로 이월할까요?`
        : `${displayEntryTitle(row)} 항목을 이번 달 결제 대상으로 되돌릴까요?`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      for (const paymentKey of row.payment_keys) {
        if (defer) await deferTollPayment(paymentKey);
        else await cancelTollDeferral(paymentKey);
      }
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        return next;
      });
      setStatus(defer ? "카드 사용내역 다음 달 이월 완료" : "카드 사용내역 이번 달 처리 대상으로 복귀");
    });
  }

  async function handleCardPaymentRowDelete(row: CardPaymentRow) {
    const confirmed = window.confirm(`${displayEntryTitle(row)} 항목을 결제 대상과 장부에서 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      for (const entryId of row.entry_ids) {
        await deleteEntry(entryId);
      }
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        return next;
      });
      setStatus(row.is_group ? "묶음 카드 사용내역 삭제 완료" : "카드 사용내역 삭제 완료");
    });
  }

  async function handleLateEntrySubmit(event: FormEvent) {
    event.preventDefault();
    const form = event.currentTarget as HTMLFormElement;
    const amount = parseAmount(lateEntryForm.amount);
    if (amount === null || amount <= 0 || (!lateEntryForm.usagePlace.trim() && !lateEntryForm.usageItem.trim())) return;
    await withRefresh(async () => {
      await createLateCardEntry({
        entry_date: lateEntryForm.date,
        usage_place: lateEntryForm.usagePlace.trim() || null,
        usage_item: lateEntryForm.usageItem.trim() || null,
        amount_value: amount,
      });
      setLateEntryForm({
        date: previousMonthLastDay(today),
        usagePlace: "",
        usageItem: "",
        amount: "",
      });
      setStatus("전월 매입 지연 내역 추가 완료");
      focusFirstDataInput(form);
    });
  }

  async function handleScheduledIncomeSave() {
    const amount = parseAmount(scheduledIncomeInput);
    if (amount === null || amount < 0) return;
    await withRefresh(async () => {
      await updateSetting("base_next_month_liquidity", String(amount));
      setScheduledIncomeInput(String(amount));
      setStatus("예정 수입 저장 완료");
    });
  }

  async function handleInterestExpenseSave() {
    const amount = parseAmount(interestExpenseInput);
    if (amount === null || amount < 0) {
      setStatus("이자지출은 0원 이상의 숫자로 입력하세요.");
      return;
    }
    await withRefresh(async () => {
      await updateSetting("interest_expense", String(amount));
      setInterestExpenseInput(String(amount));
      setStatus("이자지출 저장 완료");
    });
  }

  async function handlePasswordChange() {
    if (!passwordForm.currentPassword || !passwordForm.newPassword) {
      setStatus("현재 비밀번호와 새 비밀번호를 입력하세요.");
      return;
    }
    await withRefresh(async () => {
      await changePassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      });
      setPasswordForm({ currentPassword: "", newPassword: "" });
      setStatus("계정 비밀번호 변경 완료");
    });
  }

  async function handleLedgerReset() {
    if (!resetPassword) {
      setStatus("장부 초기화에는 현재 비밀번호가 필요합니다.");
      return;
    }
    const confirmed = window.confirm(
      "장부 데이터를 전부 초기화할까요?\n\n당월/전체 기록, 청구, 타인정산, 현금흐름, 할부, 결제 기록이 삭제됩니다. 계정과 설정은 유지됩니다.",
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await resetLedgerData(resetPassword);
      const total = Object.values(result.deleted).reduce((sum, count) => sum + count, 0);
      setResetPassword("");
      setPaymentAllocations({});
      setStatus(`장부 데이터 ${total}개 초기화 완료`);
    });
  }

  async function handleLiquidityResetAcknowledgement() {
    const confirmed = window.confirm("실제 계좌 잔액에 맞게 유동성 현황을 보정했습니까?");
    if (!confirmed) return;
    await withRefresh(async () => {
      await acknowledgeLiquidityReset();
      setStatus("유동성 보정 완료 확인");
    });
  }

  async function handleSharePinSet() {
    const pin = window.prompt("가족 공유 페이지에서 사용할 숫자 네 자리를 입력하세요.");
    if (pin === null) return;
    if (!/^[0-9]{4}$/.test(pin)) {
      setStatus("공유 PIN은 숫자 네 자리여야 합니다.");
      return;
    }
    await withRefresh(async () => {
      const result = await setSharePin(pin);
      setAuthUser((user) => (user ? { ...user, share_pin_needs_change: result.needs_change } : user));
      setStatus(
        result.needs_change
          ? "0000은 기본 PIN입니다. 공유 페이지 보호를 위해 다른 PIN으로 변경하세요."
          : "가족 공유 PIN 설정 완료. 기존 공유 세션은 종료되었습니다.",
      );
    });
  }

  async function handleAuditLogToggle() {
    if (showAuditLogs) {
      setShowAuditLogs(false);
      return;
    }
    setIsBusy(true);
    try {
      setAuditLogs(await fetchAuditLogs());
      setShowAuditLogs(true);
      setStatus("관리 로그 조회 완료");
    } catch (error) {
      setStatus(`관리 로그 조회 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAuditLogClear() {
    const confirmed = window.confirm("관리 로그를 전부 초기화할까요?\n\n이 작업은 되돌릴 수 없습니다.");
    if (!confirmed) return;
    setIsBusy(true);
    try {
      const result = await clearAuditLogs();
      setAuditLogs([]);
      setStatus(`관리 로그 ${result.deleted}개 초기화 완료`);
    } catch (error) {
      setStatus(`관리 로그 초기화 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCloseMonth() {
    const targetMonth = monthCloseStatus?.oldest_open_month;
    const isEarlyClose = Boolean(targetMonth && targetMonth === monthCloseStatus?.calendar_month);
    const confirmed = window.confirm(
      isEarlyClose
        ? `${formatMonthLabel(targetMonth!)}을 조기 월마감할까요?\n\n이후 같은 달 날짜로 추가하는 지출은 전체 기록에 바로 보관됩니다. 청구와 타인정산은 영향을 받지 않습니다.`
        : targetMonth
        ? `${formatMonthLabel(targetMonth)} 기록만 월마감하여 전체 기록으로 넘길까요?`
        : "가장 오래된 미마감 월 기록을 전체 기록으로 넘길까요?",
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await closeCurrentMonth(isEarlyClose);
      setStatus(
        result.closed_month
          ? `${formatMonthLabel(result.closed_month)} 월마감 완료: ${result.archived}개 archive`
          : "월마감할 기록이 없습니다.",
      );
    });
  }

  async function handleCsvBackupDownload() {
    setIsBusy(true);
    try {
      const { filename, blob } = await downloadCsvBackup();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      link.click();
      URL.revokeObjectURL(url);
      setStatus(`CSV 백업 생성 완료: ${filename}`);
    } catch (error) {
      setStatus(`CSV 백업 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCsvBackupImport(file: File | null) {
    if (!file) return;
    const confirmed = window.confirm(
      "CSV 백업을 복원할까요?\n\n현재 장부 데이터가 백업 파일 내용으로 교체됩니다. 사용자 계정과 관리 로그는 바꾸지 않습니다.",
    );
    if (!confirmed) {
      if (csvBackupInputRef.current) csvBackupInputRef.current.value = "";
      return;
    }
    setIsBusy(true);
    try {
      const result = await importCsvBackup(file);
      await refresh();
      const total = Object.values(result.imported).reduce((sum, count) => sum + count, 0);
      setStatus(`CSV 복원 완료: ${result.filename} (${total}행)`);
    } catch (error) {
      setStatus(`CSV 복원 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      if (csvBackupInputRef.current) csvBackupInputRef.current.value = "";
      setIsBusy(false);
    }
  }

  // 쓰기 작업을 수행한 뒤 성공하면 서버 상태를 다시 읽는다.
  async function withRefresh(action: () => Promise<void>) {
    setIsBusy(true);
    try {
      await action();
      await refresh();
    } catch (error) {
      setStatus(`작업 실패: ${error instanceof Error ? error.message : String(error)}`);
      setIsBusy(false);
    }
  }

  if (!authChecked) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <h1>money-note</h1>
          <p>서버와 통신 준비 중</p>
        </section>
      </main>
    );
  }

  if (!authUser) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <h1>money-note</h1>
          <p>가계부를 조작하려면 로그인이 필요합니다.</p>
          <form onSubmit={(event) => void handleLogin(event)}>
            <input
              value={loginForm.username}
              onChange={(event) => setLoginForm({ ...loginForm, username: event.target.value })}
              autoComplete="username"
              placeholder="아이디"
            />
            <input
              type="password"
              value={loginForm.password}
              onChange={(event) => setLoginForm({ ...loginForm, password: event.target.value })}
              autoComplete="current-password"
              placeholder="비밀번호"
            />
            <button type="submit" disabled={isBusy}>
              로그인
            </button>
          </form>
          <div className="statusline">{status}</div>
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <h1>money-note</h1>
          <p>{currentMonth} 당월 기록</p>
        </div>
        <div className="actions">
          <button type="button" onClick={() => setShowSettings(true)} disabled={isBusy}>
            설정
          </button>
          <button type="button" onClick={() => void handleCsvBackupDownload()} disabled={isBusy}>
            CSV 백업
          </button>
          <button type="button" onClick={() => csvBackupInputRef.current?.click()} disabled={isBusy}>
            CSV 복원
          </button>
          <input
            ref={csvBackupInputRef}
            type="file"
            accept=".csv,text/csv,.zip,application/zip"
            hidden
            onChange={(event) => void handleCsvBackupImport(event.target.files?.[0] ?? null)}
          />
          <button type="button" onClick={() => setShowStats(!showStats)} disabled={isBusy}>
            통계 {showStats ? "끄기" : "보기"}
          </button>
          <button type="button" onClick={() => void handleAuditLogToggle()} disabled={isBusy}>
            관리 로그
          </button>
          <button
            type="button"
            className="danger"
            onClick={() => void handleCloseMonth()}
            disabled={isBusy || !monthCloseStatus?.can_close}
          >
            월마감
          </button>
          <button type="button" onClick={() => void handleLogout()} disabled={isBusy}>
            로그아웃
          </button>
        </div>
      </header>

      <section className="statusline">{status}</section>
      {showAuditLogs ? (
        <AuditLogPanel logs={auditLogs} onClear={() => void handleAuditLogClear()} isBusy={isBusy} />
      ) : null}
      {authUser.share_pin_needs_change ? (
        <section className="security-warning">
          <div>
            <strong>가족 공유 PIN이 아직 기본값 0000입니다.</strong>
            <span>공유 링크를 보내기 전에 가족 공식 비밀번호로 변경하세요.</span>
          </div>
          <button type="button" className="save-needed" onClick={() => void handleSharePinSet()} disabled={isBusy}>
            지금 PIN 변경
          </button>
        </section>
      ) : null}
      {monthCloseStatus?.needs_close && monthCloseStatus.oldest_open_month ? (
        <section className="month-close-warning">
          <div>
            <strong>{formatMonthLabel(monthCloseStatus.oldest_open_month)} 장부가 아직 열려 있습니다.</strong>
            <span>말일 사용내역과 카드사 지연 매입을 모두 적었다면 월마감하세요. 새 달 기록은 그대로 남습니다.</span>
          </div>
          <button type="button" className="save-needed" onClick={() => void handleCloseMonth()} disabled={isBusy}>
            월마감 검토
          </button>
        </section>
      ) : null}

      <SummaryPanel
        summary={summary}
        judgment={judgment}
        labels={labels}
      />

      {showStats ? (
        <StatsModal
          items={statsItems}
          judgment={judgment}
          months={historyMonths}
          selectedMonth={selectedHistoryMonth}
          setSelectedMonth={setSelectedHistoryMonth}
          entries={historyEntries}
          onCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
          onDeleteEntry={(entry) => void handleEntryDelete(entry)}
          onClose={() => setShowStats(false)}
        />
      ) : null}

      <section className="layout">
        <div className="main-column">
          <nav className="tabs primary-tabs" aria-label="가계부 큰 탭">
            {primaryTabs.map((tab) => (
              <button
                key={tab.id}
                type="button"
                className={activePrimaryTab === tab.id ? "active" : ""}
                onClick={() => setActivePrimaryTab(tab.id)}
              >
                <span>{tab.label}</span>
                <strong>{formatWon(tab.total)}</strong>
              </button>
            ))}
          </nav>

          <section className={activePrimaryTab === "current" ? "tab-panel active" : "tab-panel"}>
            <nav className="tabs sub-tabs" aria-label="당월 하위 탭">
              {currentSubTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={activeCurrentTab === tab.id ? "active" : ""}
                  onClick={() => setActiveCurrentTab(tab.id)}
                >
                  <span>{tab.label}</span>
                  <strong>{formatWon(tab.total)}</strong>
                </button>
              ))}
            </nav>

            <DiscountPolicyBar
              month={today.slice(0, 7)}
              scope={activeCurrentTab === "settlement" ? "family" : "owner"}
              status={activeCurrentTab === "settlement" ? familyDiscountMonth : ownerDiscountMonth}
              onChange={(scope, month, policy) => void handleDiscountPolicyChange(scope, month, policy)}
              isBusy={isBusy}
            />

            <section className={activeCurrentTab === "expenses" ? "tab-panel active" : "tab-panel"}>
              <section className="panel">
                <div className="panel-header">
                  <h2>당월 지출</h2>
                  <span>{formatWon(sumAmounts(expenseEntries))}</span>
                </div>
                <form className="entry-form" onSubmit={(event) => void handleExpenseSubmit(event)}>
                  <input
                    type="date"
                    required
                    value={expenseForm.date}
                    onChange={(event) => setExpenseForm({ ...expenseForm, date: event.target.value })}
                  />
                  <input
                    required
                    value={expenseForm.usagePlace}
                    onChange={(event) => setExpenseForm({ ...expenseForm, usagePlace: event.target.value })}
                    placeholder="사용처"
                  />
                  <input
                    value={expenseForm.usageItem}
                    onChange={(event) => setExpenseForm({ ...expenseForm, usageItem: event.target.value })}
                    placeholder="세부내역"
                  />
                  <input
                    required
                    type="number"
                    min="0"
                    step="1"
                    value={expenseForm.amount}
                    onChange={(event) => setExpenseForm({ ...expenseForm, amount: event.target.value })}
                    inputMode="numeric"
                    placeholder="금액"
                  />
                  <button type="submit" disabled={isBusy}>
                    추가
                  </button>
                </form>
                <EntryTable
                  entries={expenseEntries}
                  emptyText="당월 지출이 없습니다."
                  judgment={judgment}
                  onCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
                    onDelete={(entry) => void handleEntryDelete(entry)}
                    discounts={ownerDiscountMonth?.discounts}
                    onDiscount={(entry) => void handleCurrentEntryDiscount(entry)}
                    onClearDiscount={(entry) => void handleCurrentEntryDiscountClear(entry)}
                    discountPolicy={ownerDiscountMonth?.policy}
                />
              </section>

            </section>

            {currentTabs
              .filter((tab) => tab !== "expenses")
              .map((tab) => {
                if (tab === "installments") {
                  return (
                    <section key={tab} className={activeCurrentTab === tab ? "tab-panel active" : "tab-panel"}>
                      <InstallmentTable
                        rows={installments}
                        onDelete={(installment) => void handleInstallmentDelete(installment)}
                        form={
                          <form className="installment-form" onSubmit={(event) => void handleInstallmentSubmit(event)}>
                            <input
                              value={installmentForm.title}
                              onChange={(event) => setInstallmentForm({ ...installmentForm, title: event.target.value })}
                              placeholder="세부내역"
                            />
                            <input
                              type="number"
                              min="0"
                              step="1"
                              value={installmentForm.principal}
                              onChange={(event) => setInstallmentForm({ ...installmentForm, principal: event.target.value })}
                              inputMode="numeric"
                              placeholder="할부액"
                            />
                            <input
                              value={installmentForm.fee}
                              onChange={(event) => setInstallmentForm({ ...installmentForm, fee: event.target.value })}
                              inputMode="decimal"
                              placeholder="수수료율(%)"
                            />
                            <input
                              type="number"
                              min="1"
                              value={installmentForm.months}
                              onChange={(event) => setInstallmentForm({ ...installmentForm, months: event.target.value })}
                              placeholder="개월수"
                            />
                            <button type="submit" disabled={isBusy}>
                              추가
                            </button>
                          </form>
                        }
                      />
                    </section>
                  );
                }
                return (
                  <section key={tab} className={activeCurrentTab === tab ? "tab-panel active" : "tab-panel"}>
                    <PanelTable
                      title={panelLabel(labels, tab)}
                      rows={panels.filter((panel) => panel.panel_type === tab)}
                      onDelete={(panel) => void handlePanelDelete(panel)}
                      onComplete={tab === "claim" || tab === "settlement" ? () => void handlePanelComplete(tab) : undefined}
                      onDiscount={tab === "claim" || tab === "settlement" ? (panel) => void handlePanelDiscount(panel) : undefined}
                      onClearDiscount={tab === "claim" || tab === "settlement" ? (panel) => void handlePanelDiscountClear(panel) : undefined}
                      discountPolicy={tab === "settlement" ? familyDiscountMonth?.policy : ownerDiscountMonth?.policy}
                      judgment={judgment}
                      onShare={tab === "claim" || tab === "settlement" ? () => void handlePanelShare(tab) : undefined}
                      form={
                        <PanelAppendForm
                          isBusy={isBusy}
                          panelType={tab}
                          panelForm={panelForm}
                          setPanelForm={setPanelForm}
                          handlePanelSubmit={handlePanelSubmit}
                        />
                      }
                    />
                    {tab === "settlement" ? (
                      <CreditUsagePanel
                        cardLimit={parseSettingNumber(settings, "settlement_card_limit", 5_800_000)}
                        currentCardTotal={sumAmounts(expenseEntries) + sumInstallmentMonthlyAmounts(installments)}
                        settlementTotal={sumPanelAmounts(panels.filter((panel) => panel.panel_type === "settlement"))}
                        tone={judgment?.credit ?? null}
                      />
                    ) : null}
                  </section>
                );
              })}
          </section>

          <section className={activePrimaryTab === "fixed" ? "tab-panel active" : "tab-panel"}>
            <PanelTable
              title={panelLabel(labels, "fixed")}
              rows={panels.filter((panel) => panel.panel_type === "fixed")}
              onDelete={(panel) => void handlePanelDelete(panel)}
              form={
                <PanelAppendForm
                  isBusy={isBusy}
                  panelType="fixed"
                  panelForm={panelForm}
                  setPanelForm={setPanelForm}
                  handlePanelSubmit={handlePanelSubmit}
                />
              }
            />
            <section className="panel">
              <div className="panel-header">
                <h2>카드 정기결제</h2>
                <span>{formatWon(sumAmounts(plannedEntries))}</span>
              </div>
              <form className="planned-form" onSubmit={(event) => void handlePlannedSubmit(event)}>
                <input
                  type="number"
                  min="1"
                  max="31"
                  required
                  value={plannedForm.dueDay}
                  onChange={(event) => setPlannedForm({ ...plannedForm, dueDay: event.target.value })}
                  placeholder="결제일"
                />
                <input
                  required
                  value={plannedForm.usagePlace}
                  onChange={(event) => setPlannedForm({ ...plannedForm, usagePlace: event.target.value })}
                  placeholder="사용처"
                />
                <input
                  value={plannedForm.usageItem}
                  onChange={(event) => setPlannedForm({ ...plannedForm, usageItem: event.target.value })}
                  placeholder="세부내역"
                />
                <input
                  required
                  type="number"
                  min="0"
                  step="1"
                  value={plannedForm.amount}
                  onChange={(event) => setPlannedForm({ ...plannedForm, amount: event.target.value })}
                  inputMode="numeric"
                  placeholder="금액"
                />
                <button type="submit" disabled={isBusy}>
                  추가
                </button>
              </form>
              <PlannedTable
                entries={plannedEntries}
                emptyText="카드 정기결제 항목이 없습니다."
                onConfirm={(entry) => void handlePlannedConfirm(entry)}
                onDelete={(entry) => void handlePlannedDelete(entry)}
              />
            </section>
          </section>

          <section className={activePrimaryTab === "payment" ? "tab-panel active" : "tab-panel"}>
            <CardPaymentPanel
              status={cardPayments}
              fallbackLiquidity={parseSettingNumber(settings, "base_next_month_liquidity", 400_000)}
              availableLiquidity={summary?.liquidity_status ?? 0}
              onAcknowledgeLiquidityReset={() => void handleLiquidityResetAcknowledgement()}
              allocations={paymentAllocations}
              setAllocations={setPaymentAllocations}
              paymentBudget={paymentBudget}
              setPaymentBudget={setPaymentBudget}
              onDiscountPolicyChange={(policy) =>
                void handleDiscountPolicyChange("owner", cardPayments?.usage_month ?? today.slice(0, 7), policy)
              }
              onAutoAllocate={handleAutoAllocate}
              onSelect={handlePaymentSelection}
              onSubmit={() => void handleCardPaymentSubmit()}
              onDeleteEvent={(eventId) => void handleCardPaymentEventDelete(eventId)}
              onDeleteRow={(row) => void handleCardPaymentRowDelete(row)}
              onTollDeferral={(row, defer) => void handleTollDeferral(row, defer)}
              paymentTone={judgment?.payment ?? null}
              lateEntryForm={lateEntryForm}
              setLateEntryForm={setLateEntryForm}
              onLateEntrySubmit={handleLateEntrySubmit}
              isBusy={isBusy}
            />
          </section>

          <section className={activePrimaryTab === "frozen" ? "tab-panel active" : "tab-panel"}>
            <PanelTable
              title={panelLabel(labels, "frozen")}
              rows={panels.filter((panel) => panel.panel_type === "frozen")}
              onDelete={(panel) => void handlePanelDelete(panel)}
              form={
                <PanelAppendForm
                  isBusy={isBusy}
                  panelType="frozen"
                  panelForm={panelForm}
                  setPanelForm={setPanelForm}
                  handlePanelSubmit={handlePanelSubmit}
                />
              }
            />
          </section>

          <section className={activePrimaryTab === "cash" ? "tab-panel active" : "tab-panel"}>
            <CashFlowPanel
              rows={cashFlows}
              form={cashFlowForm}
              setForm={setCashFlowForm}
              onSubmit={handleCashFlowSubmit}
              onDelete={(flow) => void handleCashFlowDelete(flow)}
              isBusy={isBusy}
            />
          </section>

        </div>
      </section>

      {showSettings ? (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setShowSettings(false)}>
          <section
            className="settings-modal"
            role="dialog"
            aria-modal="true"
            aria-label="설정"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <div className="panel-header">
              <h2>설정</h2>
              <button type="button" onClick={() => setShowSettings(false)}>
                닫기
              </button>
            </div>
            <div className="settings-grid">
              <label>
                <span>예정 수입</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={scheduledIncomeInput}
                  onChange={(event) => setScheduledIncomeInput(event.target.value)}
                  inputMode="numeric"
                  placeholder="예정 수입"
                />
                <button type="button" onClick={() => void handleScheduledIncomeSave()} disabled={isBusy}>
                  저장
                </button>
              </label>
              <label>
                <span>이자지출</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  value={interestExpenseInput}
                  onChange={(event) => setInterestExpenseInput(event.target.value)}
                  inputMode="numeric"
                  placeholder="이자지출"
                />
                <button type="button" onClick={() => void handleInterestExpenseSave()} disabled={isBusy}>
                  저장
                </button>
              </label>
              <div className="settings-row">
                <span>가족 공유 PIN</span>
                <button type="button" onClick={() => void handleSharePinSet()} disabled={isBusy}>
                  PIN 변경
                </button>
              </div>
              <label>
                <span>계정 비밀번호</span>
                <input
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(event) => setPasswordForm({ ...passwordForm, currentPassword: event.target.value })}
                  autoComplete="current-password"
                  placeholder="현재 비밀번호"
                />
                <input
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(event) => setPasswordForm({ ...passwordForm, newPassword: event.target.value })}
                  autoComplete="new-password"
                  placeholder="새 비밀번호"
                />
                <button type="button" onClick={() => void handlePasswordChange()} disabled={isBusy}>
                  변경
                </button>
              </label>
              <section className="danger-zone">
                <div>
                  <h3>장부 데이터 전체 초기화</h3>
                  <p>계정, 로그인 세션, 공유 PIN, 설정은 유지하고 사용자가 입력한 장부 운용 데이터만 삭제합니다.</p>
                </div>
                <input
                  type="password"
                  value={resetPassword}
                  onChange={(event) => setResetPassword(event.target.value)}
                  autoComplete="current-password"
                  placeholder="현재 비밀번호"
                />
                <button type="button" className="danger" onClick={() => void handleLedgerReset()} disabled={isBusy}>
                  전체 초기화
                </button>
              </section>
            </div>
          </section>
        </div>
      ) : null}

    </main>
  );
}
