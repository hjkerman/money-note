import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  AuditLog,
  CardPaymentRow,
  CardPaymentStatus,
  CashFlow,
  Installment,
  LedgerEntry,
  MonthlyPanel,
  MonthCloseStatus,
  Settings,
  SpendingCategory,
  Summary,
  acknowledgeLiquidityReset,
  appendPlannedEntry,
  cancelTollDeferral,
  clearAuditLogs,
  closeCurrentMonth,
  completePanelsByType,
  confirmFrozenPanel,
  confirmPlannedEntry,
  createCashFlow,
  createCardPaymentEvent,
  createEntry,
  createExport,
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
  fetchCashFlows,
  fetchCurrentCardPayments,
  fetchArchiveEntries,
  fetchAuditLogs,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchInstallments,
  fetchLabels,
  fetchMe,
  fetchMonthCloseStatus,
  fetchSettings,
  fetchSummary,
  latestExportUrl,
  login,
  logout,
  setSharePin,
  updateEntry,
  updateSetting,
} from "./api";
import {
  budgetCommitteeTone,
  categoryLabel,
  classifyClaimPanel,
  creditUsageTone,
  paymentPressureTone,
  spendingStatTones,
} from "./judgment";

type PanelType = MonthlyPanel["panel_type"];
type PrimaryTab = "current" | "payment" | "fixed" | "frozen" | "cash";
type CurrentTab = "expenses" | "claim" | "settlement" | "installments";
type StatItem = {
  amount_value: number | null;
  spending_category: SpendingCategory | null;
};

const panelMeta: Record<PanelType, { labelKey: string; fallback: string }> = {
  fixed: { labelKey: "panel_fixed_title", fallback: "현금성 고정지출" },
  frozen: { labelKey: "panel_frozen_title", fallback: "동결" },
  claim: { labelKey: "panel_claim_title", fallback: "청구" },
  settlement: { labelKey: "panel_settlement_title", fallback: "타인정산" },
};

const today = new Date().toISOString().slice(0, 10);
const currentTabs: CurrentTab[] = ["expenses", "claim", "settlement", "installments"];
const hasOwn = (record: object, key: PropertyKey) => Object.prototype.hasOwnProperty.call(record, key);

export function App() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [archiveEntries, setArchiveEntries] = useState<LedgerEntry[]>([]);
  const [panels, setPanels] = useState<MonthlyPanel[]>([]);
  const [cashFlows, setCashFlows] = useState<CashFlow[]>([]);
  const [installments, setInstallments] = useState<Installment[]>([]);
  const [cardPayments, setCardPayments] = useState<CardPaymentStatus | null>(null);
  const [monthCloseStatus, setMonthCloseStatus] = useState<MonthCloseStatus | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
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
    amount: string;
    dueDay: string;
  }>({ panel_type: "fixed", title: "", amount: "", dueDay: "" });
  const [activePrimaryTab, setActivePrimaryTab] = useState<PrimaryTab>("current");
  const [activeCurrentTab, setActiveCurrentTab] = useState<CurrentTab>("expenses");
  const [selectedHistoryMonth, setSelectedHistoryMonth] = useState(today.slice(0, 7));
  const [showStats, setShowStats] = useState(false);
  const [showAuditLogs, setShowAuditLogs] = useState(false);
  const [pendingCategoryChanges, setPendingCategoryChanges] = useState<Record<number, SpendingCategory | null>>({});
  const [paymentAllocations, setPaymentAllocations] = useState<Record<string, string>>({});
  const [paymentBudget, setPaymentBudget] = useState("");
  const [fallbackLiquidityInput, setFallbackLiquidityInput] = useState("");
  const [isDiscountMode, setIsDiscountMode] = useState(false);
  const [lateEntryForm, setLateEntryForm] = useState({
    date: previousMonthLastDay(today),
    usagePlace: "",
    usageItem: "",
    amount: "",
  });

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
    () => activeStatItems(activePrimaryTab, activeCurrentTab, expenseEntries, historyEntries, panels, pendingCategoryChanges),
    [activeCurrentTab, activePrimaryTab, expenseEntries, historyEntries, panels, pendingCategoryChanges],
  );
  const hasPendingCategoryChanges = Object.keys(pendingCategoryChanges).length > 0;

  useEffect(() => {
    if (!hasPendingCategoryChanges) return;
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "저장하지 않고 나가시겠습니까?";
    };
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  }, [hasPendingCategoryChanges]);
  const primaryTabs: { id: PrimaryTab; label: string; total: number }[] = [
    {
      id: "current",
      label: "당월",
      total:
        sumAmounts(expenseEntries) +
        sumInstallmentMonthlyAmounts(installments) +
        sumPanelAmounts(panels.filter((panel) => panel.panel_type === "claim")) +
        sumPanelAmounts(panels.filter((panel) => panel.panel_type === "settlement")),
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
      total: sumPanelAmounts(panels.filter((panel) => panel.panel_type === "claim")),
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
      const [
        nextEntries,
        nextArchiveEntries,
        nextPanels,
        nextSummary,
        nextLabels,
        nextCashFlows,
        nextSettings,
        nextInstallments,
        nextCardPayments,
        nextMonthCloseStatus,
      ] = await Promise.all([
        fetchCurrentEntries(),
        fetchArchiveEntries(),
        fetchCurrentPanels(),
        fetchSummary(),
        fetchLabels(),
        fetchCashFlows(),
        fetchSettings(),
        fetchInstallments(),
        fetchCurrentCardPayments(),
        fetchMonthCloseStatus(),
      ]);
      setEntries(nextEntries);
      setArchiveEntries(nextArchiveEntries);
      setPanels(nextPanels);
      setSummary(nextSummary);
      setLabels(nextLabels);
      setCashFlows(nextCashFlows);
      setSettings(nextSettings);
      setInstallments(nextInstallments);
      setCardPayments(nextCardPayments);
      setMonthCloseStatus(nextMonthCloseStatus);
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

  // 사용처와 사용항목을 합쳐 기존 Excel 적요 형식으로도 호환되는 당월 기록을 만든다.
  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    const usagePlace = expenseForm.usagePlace.trim();
    const usageItem = expenseForm.usageItem.trim();
    if (!usagePlace && !usageItem) return;
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
        amount_value: parseAmount(expenseForm.amount),
        amount_expr: null,
        aux_amount_value: null,
        aux_amount_expr: null,
        extra_value: null,
        sort_order: nextSortOrder(entries),
        due_day: null,
        confirmed_at: null,
        spending_category: null,
      });
      setExpenseForm({ date: expenseForm.date, usagePlace: "", usageItem: "", amount: "" });
      setStatus(created.book_section === "archive" ? "이미 마감한 달의 전체 기록에 추가 완료" : "당월 기록 추가 완료");
    });
  }

  async function handlePlannedSubmit(event: FormEvent) {
    event.preventDefault();
    const usagePlace = plannedForm.usagePlace.trim();
    const usageItem = plannedForm.usageItem.trim();
    if (!usagePlace && !usageItem) return;
    await withRefresh(async () => {
      await appendPlannedEntry({
        title: formatUsageTitle(usagePlace, usageItem),
        usage_place: usagePlace || null,
        usage_item: usageItem || null,
        amount_value: parseAmount(plannedForm.amount),
        due_day: parseOptionalDay(plannedForm.dueDay),
      });
      setPlannedForm({ dueDay: "", usagePlace: "", usageItem: "", amount: "" });
      setStatus("카드 정기결제 추가 완료");
    });
  }

  async function handlePanelSubmit(event: FormEvent, panelType = panelForm.panel_type) {
    event.preventDefault();
    if (!panelForm.title.trim()) return;
    await withRefresh(async () => {
      const sameTypePanels = panels.filter((panel) => panel.panel_type === panelType);
      await createPanel({
        month: monthCloseStatus?.calendar_month ?? today.slice(0, 7),
        panel_type: panelType,
        title: panelForm.title.trim(),
        amount_value: parseAmount(panelForm.amount),
        amount_expr: null,
        sort_order: nextSortOrder(sameTypePanels),
        due_day: null,
        confirmed_at: null,
      });
      setPanelForm({ panel_type: panelType, title: "", amount: "", dueDay: "" });
      setStatus(`${panelLabel(labels, panelType)} 항목 추가 완료`);
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

  async function handleFrozenConfirm(panel: MonthlyPanel) {
    const confirmed = window.confirm(`${panel.title} 동결을 풀고 당월 기록에 추가할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await confirmFrozenPanel(panel.id);
      setStatus(`${panel.title} 동결 해제 완료`);
    });
  }

  // 분류 변경은 즉시 저장하지 않고 pending 상태로 모아 사용자가 저장 버튼을 누르게 한다.
  async function handleCategoryChange(entry: LedgerEntry, category: SpendingCategory | null) {
    const original = entry.spending_category;
    setPendingCategoryChanges((current) => {
      const next = { ...current };
      if (category === original) {
        delete next[entry.id];
      } else {
        next[entry.id] = category;
      }
      return next;
    });
    setStatus("저장되지 않은 변경 사항이 있습니다.");
  }

  async function handleEntryDelete(entry: LedgerEntry) {
    const confirmed = window.confirm(`${entry.title} 기록을 삭제할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deleteEntry(entry.id);
      setStatus("당월 기록 삭제 완료");
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

  // pending 분류 변경을 서버에 일괄 저장한다.
  async function handleSavePendingChanges() {
    const changes = Object.entries(pendingCategoryChanges);
    if (!changes.length) return;
    await withRefresh(async () => {
      await Promise.all(
        changes.map(([entryId, category]) =>
          updateEntry(Number(entryId), { spending_category: category }),
        ),
      );
      setPendingCategoryChanges({});
      setStatus(`변경 사항 ${changes.length}개 저장 완료`);
    });
  }

  async function handleCashFlowSubmit(event: FormEvent) {
    event.preventDefault();
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
      if (row.is_toll && row.remaining_amount > remainingBudget) continue;
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
      .map(([entry_payment_key, amountText]) => ({
        entry_payment_key,
        amount_value: parseAmount(amountText) ?? 0,
      }))
      .filter((allocation) => allocation.amount_value > 0);
    if (!allocations.length) return;
    const total = allocations.reduce((sum, allocation) => sum + allocation.amount_value, 0);
    const kind = isDiscountMode ? "할인액" : "즉시결제";
    const confirmed = window.confirm(`${kind} ${formatWon(total)}을 선택한 사용내역에 반영할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await createCardPaymentEvent({
        event_date: today,
        event_type: isDiscountMode ? "discount" : "immediate",
        note: "",
        allocations,
      });
      setPaymentAllocations({});
      setStatus(`${kind} 반영 완료`);
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

  async function handleTollDeferral(row: CardPaymentRow, defer: boolean) {
    if (!row.payment_key) return;
    const confirmed = window.confirm(
      defer
        ? `${displayEntryTitle(row)} 항목을 다음 달 결제로 이월할까요?`
        : `${displayEntryTitle(row)} 항목을 이번 달 결제 대상으로 되돌릴까요?`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      if (defer) await deferTollPayment(row.payment_key as string);
      else await cancelTollDeferral(row.payment_key as string);
      setPaymentAllocations((current) => {
        const next = { ...current };
        delete next[row.payment_key as string];
        return next;
      });
      setStatus(defer ? "통행료 다음 달 이월 완료" : "통행료 이번 달 처리 대상으로 복귀");
    });
  }

  async function handleLateEntrySubmit(event: FormEvent) {
    event.preventDefault();
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
    });
  }

  async function handleFallbackLiquiditySave() {
    const amount = parseAmount(fallbackLiquidityInput);
    if (amount === null || amount < 0) return;
    await withRefresh(async () => {
      await updateSetting("base_next_month_liquidity", String(amount));
      setFallbackLiquidityInput("");
      setStatus("기본 심사 기준액 저장 완료");
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

  async function handleExport() {
    await withRefresh(async () => {
      const result = await createExport();
      setStatus(`엑셀 export 완료: ${result.filename}`);
      window.location.href = latestExportUrl();
    });
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
          <span className="user-badge">{authUser.display_name}</span>
          <button type="button" onClick={() => void refresh()} disabled={isBusy}>
            새로고침
          </button>
          <button type="button" onClick={() => void handleSharePinSet()} disabled={isBusy}>
            공유 PIN 설정
          </button>
          {hasPendingCategoryChanges ? (
            <button type="button" className="save-needed" onClick={() => void handleSavePendingChanges()} disabled={isBusy}>
              변경 사항 저장
            </button>
          ) : null}
          <button type="button" onClick={() => void handleExport()} disabled={isBusy}>
            엑셀 export
          </button>
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

      <SummaryPanel summary={summary} labels={labels} entries={expenseEntries} panels={panels} cashFlows={cashFlows} />

      {showStats ? (
        <section className="insight-stack" aria-label="통계와 월별 기록">
          <StatsPanel items={statsItems} />
          <HistoryPanel
            months={historyMonths}
            selectedMonth={selectedHistoryMonth}
            setSelectedMonth={setSelectedHistoryMonth}
            entries={historyEntries}
            pendingCategoryChanges={pendingCategoryChanges}
            onCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
          />
        </section>
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

            <section className={activeCurrentTab === "expenses" ? "tab-panel active" : "tab-panel"}>
              <section className="panel">
                <div className="panel-header">
                  <h2>당월 지출</h2>
                  <span>{formatWon(sumAmounts(expenseEntries))}</span>
                </div>
                <EntryTable
                  entries={expenseEntries}
                  emptyText="당월 지출이 없습니다."
                  pendingCategoryChanges={pendingCategoryChanges}
                  onCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
                  onDelete={(entry) => void handleEntryDelete(entry)}
                />
                <form className="entry-form" onSubmit={(event) => void handleExpenseSubmit(event)}>
                  <input
                    type="date"
                    value={expenseForm.date}
                    onChange={(event) => setExpenseForm({ ...expenseForm, date: event.target.value })}
                  />
                  <input
                    value={expenseForm.usagePlace}
                    onChange={(event) => setExpenseForm({ ...expenseForm, usagePlace: event.target.value })}
                    placeholder="사용처"
                  />
                  <input
                    value={expenseForm.usageItem}
                    onChange={(event) => setExpenseForm({ ...expenseForm, usageItem: event.target.value })}
                    placeholder="사용항목"
                  />
                  <input
                    value={expenseForm.amount}
                    onChange={(event) => setExpenseForm({ ...expenseForm, amount: event.target.value })}
                    inputMode="numeric"
                    placeholder="금액"
                  />
                  <button type="submit" disabled={isBusy}>
                    추가
                  </button>
                </form>
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
                              placeholder="적요"
                            />
                            <input
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
              <PlannedTable
                entries={plannedEntries}
                emptyText="카드 정기결제 항목이 없습니다."
                onConfirm={(entry) => void handlePlannedConfirm(entry)}
                onDelete={(entry) => void handlePlannedDelete(entry)}
              />
              <form className="planned-form" onSubmit={(event) => void handlePlannedSubmit(event)}>
                <input
                  type="number"
                  min="1"
                  max="31"
                  value={plannedForm.dueDay}
                  onChange={(event) => setPlannedForm({ ...plannedForm, dueDay: event.target.value })}
                  placeholder="결제일"
                />
                <input
                  value={plannedForm.usagePlace}
                  onChange={(event) => setPlannedForm({ ...plannedForm, usagePlace: event.target.value })}
                  placeholder="사용처"
                />
                <input
                  value={plannedForm.usageItem}
                  onChange={(event) => setPlannedForm({ ...plannedForm, usageItem: event.target.value })}
                  placeholder="사용항목"
                />
                <input
                  value={plannedForm.amount}
                  onChange={(event) => setPlannedForm({ ...plannedForm, amount: event.target.value })}
                  inputMode="numeric"
                  placeholder="금액"
                />
                <button type="submit" disabled={isBusy}>
                  추가
                </button>
              </form>
            </section>
          </section>

          <section className={activePrimaryTab === "payment" ? "tab-panel active" : "tab-panel"}>
            <CardPaymentPanel
              status={cardPayments}
              fallbackLiquidity={parseSettingNumber(settings, "base_next_month_liquidity", 400_000)}
              availableLiquidity={summary?.liquidity_status ?? 0}
              fallbackLiquidityInput={fallbackLiquidityInput}
              setFallbackLiquidityInput={setFallbackLiquidityInput}
              onFallbackLiquiditySave={() => void handleFallbackLiquiditySave()}
              onAcknowledgeLiquidityReset={() => void handleLiquidityResetAcknowledgement()}
              allocations={paymentAllocations}
              setAllocations={setPaymentAllocations}
              paymentBudget={paymentBudget}
              setPaymentBudget={setPaymentBudget}
              isDiscountMode={isDiscountMode}
              setIsDiscountMode={setIsDiscountMode}
              onAutoAllocate={handleAutoAllocate}
              onSelect={handlePaymentSelection}
              onSubmit={() => void handleCardPaymentSubmit()}
              onDeleteEvent={(eventId) => void handleCardPaymentEventDelete(eventId)}
              onTollDeferral={(row, defer) => void handleTollDeferral(row, defer)}
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
              onConfirmFrozen={(panel) => void handleFrozenConfirm(panel)}
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
    </main>
  );
}

function SummaryPanel({
  summary,
  labels,
  entries,
  panels,
  cashFlows,
}: {
  summary: Summary | null;
  labels: Record<string, string>;
  entries: LedgerEntry[];
  panels: MonthlyPanel[];
  cashFlows: CashFlow[];
}) {
  const claimRows = panels.filter((panel) => panel.panel_type === "claim");
  const settlementRows = panels.filter((panel) => panel.panel_type === "settlement");
  const frozenRows = panels.filter((panel) => panel.panel_type === "frozen");
  const committee = budgetCommitteeTone({
    expenseTotal: sumAmounts(entries),
    expenseCount: entries.length,
    cashFlowTotal: sumCashFlows(cashFlows),
    cashFlowCount: cashFlows.length,
    claimTotal: sumPanelAmounts(claimRows),
    claimCount: claimRows.length,
    settlementTotal: sumPanelAmounts(settlementRows),
    settlementCount: settlementRows.length,
    frozenTotal: sumPanelAmounts(frozenRows),
    frozenCount: frozenRows.length,
  });
  const rows = summary
    ? [
        [labels.summary_card_total_label ?? "카드대금", summary.card_total],
        [labels.summary_transfer_or_deposit_label ?? "송금/예치", summary.transfer_or_deposit_total],
        [labels.summary_interest_expense_label ?? "이자지출", summary.interest_expense],
        [labels.summary_frozen_asset_label ?? "동결자산", summary.frozen_asset_total],
        [labels.summary_liquidity_status_label ?? "유동성 현황", summary.liquidity_status],
        [labels.summary_next_month_liquidity_label ?? "익월 유동성", summary.next_month_liquidity],
      ]
    : [];

  return (
    <section className="panel summary-panel">
      <div className="panel-header">
        <h2>{labels.summary_title ?? "요약"} / 인사이트</h2>
      </div>
      {summary ? (
        <>
          <p className={`committee-verdict ${committee.level}`}>{committee.message}</p>
          <dl>
            {rows.map(([label, value]) => (
              <div key={label} className={label === (labels.summary_next_month_liquidity_label ?? "익월 유동성") ? "total" : ""}>
                <dt>{label}</dt>
                <dd>{formatWon(value as number)}</dd>
              </div>
            ))}
          </dl>
        </>
      ) : (
        <p className="empty">요약을 불러오는 중입니다.</p>
      )}
    </section>
  );
}

function AuditLogPanel({ logs, onClear, isBusy }: { logs: AuditLog[]; onClear: () => void; isBusy: boolean }) {
  return (
    <section className="panel audit-panel">
      <div className="panel-header">
        <div>
          <h2>관리 로그</h2>
          <p>변경 API의 경로와 처리 결과만 기록합니다. 요청 본문과 비밀번호는 저장하지 않습니다.</p>
        </div>
        <button type="button" className="danger" onClick={onClear} disabled={isBusy || !logs.length}>
          로그 초기화
        </button>
      </div>
      {logs.length ? (
        <table>
          <thead>
            <tr>
              <th>시각</th>
              <th>사용자</th>
              <th>요청</th>
              <th>경로</th>
              <th className="amount">결과</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td className="date">{formatAuditTimestamp(log.occurred_at)}</td>
                <td>{log.actor_username}</td>
                <td>{log.method}</td>
                <td className="audit-path">{log.path}</td>
                <td className="amount">{log.status_code}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">기록된 변경 로그가 없습니다.</p>
      )}
    </section>
  );
}

function StatsPanel({ items }: { items: StatItem[] }) {
  const rows = spendingStatTones().map((tone) => ({
    ...tone,
    amount: sumStatItems(
      items.filter((item) =>
        tone.key === null ? !item.spending_category : item.spending_category === tone.key,
      ),
    ),
  }));
  const total = sumStatItems(items);
  return (
    <section className="panel stats-panel">
      <div className="panel-header">
        <h2>소비 통계</h2>
        <span>{formatWon(total)}</span>
      </div>
      <div className="stats-grid">
        {rows.map((row) => (
          <div key={row.title}>
            <strong>{row.title}</strong>
            <span>{formatWon(row.amount)}</span>
            <p>{row.caption}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function CreditUsagePanel({
  cardLimit,
  currentCardTotal,
  settlementTotal,
}: {
  cardLimit: number;
  currentCardTotal: number;
  settlementTotal: number;
}) {
  const combinedTotal = currentCardTotal + settlementTotal;
  const usageRate = cardLimit > 0 ? combinedTotal / cardLimit : 0;
  const usagePercent = usageRate * 100;
  const width = Math.min(100, Math.max(0, usagePercent));
  const tone = creditUsageTone(usageRate);
  return (
    <section className={`panel credit-panel ${tone.level}`}>
      <div className="panel-header">
        <h2>가족카드 한도 감시</h2>
        <span>{usagePercent.toFixed(1)}%</span>
      </div>
      <div className="credit-meter" aria-label={`카드 한도 사용률 ${usagePercent.toFixed(1)}%`}>
        <div style={{ width: `${width}%` }} />
      </div>
      <dl className="credit-stats">
        <div>
          <dt>추정 합산 사용액</dt>
          <dd>{formatWon(combinedTotal)}</dd>
        </div>
        <div>
          <dt>카드 한도</dt>
          <dd>{formatWon(cardLimit)}</dd>
        </div>
      </dl>
      <p>{tone.message}</p>
      <p className="credit-note">할부와 일시불이 섞이면 실제 한도 차감액은 카드사 기준과 다를 수 있습니다.</p>
    </section>
  );
}

function CardPaymentPanel({
  status,
  fallbackLiquidity,
  availableLiquidity,
  fallbackLiquidityInput,
  setFallbackLiquidityInput,
  onFallbackLiquiditySave,
  onAcknowledgeLiquidityReset,
  allocations,
  setAllocations,
  paymentBudget,
  setPaymentBudget,
  isDiscountMode,
  setIsDiscountMode,
  onAutoAllocate,
  onSelect,
  onSubmit,
  onDeleteEvent,
  onTollDeferral,
  lateEntryForm,
  setLateEntryForm,
  onLateEntrySubmit,
  isBusy,
}: {
  status: CardPaymentStatus | null;
  fallbackLiquidity: number;
  availableLiquidity: number;
  fallbackLiquidityInput: string;
  setFallbackLiquidityInput: (value: string) => void;
  onFallbackLiquiditySave: () => void;
  onAcknowledgeLiquidityReset: () => void;
  allocations: Record<string, string>;
  setAllocations: (value: Record<string, string>) => void;
  paymentBudget: string;
  setPaymentBudget: (value: string) => void;
  isDiscountMode: boolean;
  setIsDiscountMode: (value: boolean) => void;
  onAutoAllocate: () => void;
  onSelect: (row: CardPaymentRow, selected: boolean) => void;
  onSubmit: () => void;
  onDeleteEvent: (eventId: number) => void;
  onTollDeferral: (row: CardPaymentRow, defer: boolean) => void;
  lateEntryForm: { date: string; usagePlace: string; usageItem: string; amount: string };
  setLateEntryForm: (value: { date: string; usagePlace: string; usageItem: string; amount: string }) => void;
  onLateEntrySubmit: (event: FormEvent) => Promise<void>;
  isBusy: boolean;
}) {
  if (!status) {
    return <section className="panel"><p className="empty">결제 현황을 불러오는 중입니다.</p></section>;
  }
  const daysUntilDue = daysBetween(today, status.due_date);
  const referenceLiquidity = status.primary_income_total > 0 ? status.primary_income_total : fallbackLiquidity;
  const pressure = paymentPressureTone(status.recorded_remaining_total, daysUntilDue, referenceLiquidity);
  const selectedTotal = sumPaymentAllocationInputs(allocations);
  return (
    <section className="payment-stack">
      <section className={`panel payment-overview ${pressure.level}`}>
        <div className="panel-header">
          <div>
            <h2>이번달 결제</h2>
            <p>{formatMonthLabel(status.usage_month)} 사용분 · {formatDateLabel(status.due_date)}까지 즉시결제 가능</p>
          </div>
          <span>{formatWon(status.effective_remaining_total)}</span>
        </div>
        {status.needs_liquidity_reset ? (
          <div className="payment-alert">
            <span>결제 안 된 내역 있습니다. 유동성 현황을 재설정하세요.</span>
            <button type="button" onClick={onAcknowledgeLiquidityReset}>유동성 보정 완료</button>
          </div>
        ) : null}
        <p className="judgment-line">{pressure.message}</p>
        <dl className="payment-summary">
          <div><dt>심사 기준 수입</dt><dd>{formatWon(referenceLiquidity)}</dd></div>
          <div><dt>원래 결제액</dt><dd>{formatWon(status.original_total)}</dd></div>
          <div><dt>즉시결제 누적</dt><dd>{formatWon(status.immediate_paid_total)}</dd></div>
          <div><dt>할인액 누적</dt><dd>{formatWon(status.discount_total)}</dd></div>
          <div><dt>기록상 미결제</dt><dd>{formatWon(status.recorded_remaining_total)}</dd></div>
        </dl>
        <div className="fallback-setting">
          <span>주 수입이 없는 달에 사용할 기본 심사 기준액: {formatWon(fallbackLiquidity)}</span>
          <input
            value={fallbackLiquidityInput}
            onChange={(event) => setFallbackLiquidityInput(event.target.value)}
            inputMode="numeric"
            placeholder="새 기본 기준액"
          />
          <button type="button" onClick={onFallbackLiquiditySave} disabled={isBusy}>저장</button>
        </div>
        <div className="payment-controls">
          <label className="payment-budget-field">
            <span>자동 배분 한도</span>
            <input
              value={paymentBudget}
              onChange={(event) => setPaymentBudget(event.target.value)}
              inputMode="numeric"
              placeholder={`미입력 시 ${formatWon(availableLiquidity)}`}
            />
          </label>
          <button type="button" onClick={onAutoAllocate} disabled={isBusy || !status.immediate_allowed}>
            날짜순 자동 배분
          </button>
          <label className="check-label">
            <input
              type="checkbox"
              checked={isDiscountMode}
              onChange={(event) => setIsDiscountMode(event.target.checked)}
            />
            할인액 처리
          </label>
          <button type="button" onClick={() => setAllocations({})} disabled={isBusy}>선택 해제</button>
          <button type="button" className="save-needed" onClick={onSubmit} disabled={isBusy || selectedTotal <= 0 || !status.immediate_allowed}>
            {isDiscountMode ? "할인액 반영" : "즉시결제 반영"} {formatWon(selectedTotal)}
          </button>
        </div>
      </section>

      <section className="panel late-entry-panel">
        <div className="panel-header">
          <div>
            <h2>전월 매입 지연 보정</h2>
            <p>카드사가 월말 뒤에 올린 직전월 사용내역을 추가합니다. 과거 기록은 삭제하지 않습니다.</p>
          </div>
          <span>{status.rows.filter((row) => row.entry_kind === "late_expense").length}건</span>
        </div>
        {status.rows.some((row) => row.entry_kind === "late_expense") ? (
          <table>
            <thead><tr><th>날짜</th><th>적요</th><th className="amount">금액</th></tr></thead>
            <tbody>
              {status.rows.filter((row) => row.entry_kind === "late_expense").map((row) => (
                <tr key={row.id}>
                  <td className="date">{row.date_label}</td>
                  <td>{displayEntryTitle(row)}</td>
                  <td className="amount">{formatWon(row.amount_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="empty">카드사가 뒤늦게 제출한 전월 내역이 없습니다.</p>}
        <form className="entry-form" onSubmit={(event) => void onLateEntrySubmit(event)}>
          <input
            type="date"
            value={lateEntryForm.date}
            min={previousMonthFirstDay(today)}
            max={previousMonthLastDay(today)}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, date: event.target.value })}
          />
          <input
            value={lateEntryForm.usagePlace}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, usagePlace: event.target.value })}
            placeholder="사용처"
          />
          <input
            value={lateEntryForm.usageItem}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, usageItem: event.target.value })}
            placeholder="사용항목"
          />
          <input
            value={lateEntryForm.amount}
            onChange={(event) => setLateEntryForm({ ...lateEntryForm, amount: event.target.value })}
            inputMode="numeric"
            placeholder="금액"
          />
          <button type="submit" disabled={isBusy}>추가</button>
        </form>
      </section>

      <section className="panel payment-ledger">
        <div className="panel-header">
          <h2>결제 대상 사용내역</h2>
          <span>{status.rows.filter((row) => !row.is_deferred && row.remaining_amount > 0).length}건</span>
        </div>
        {status.rows.length ? (
          <table>
            <thead>
              <tr>
                <th className="select-cell">선택</th>
                <th>날짜</th>
                <th>적요</th>
                <th className="amount">원래 금액</th>
                <th className="amount">즉시결제</th>
                <th className="amount">할인</th>
                <th className="amount">남은 금액</th>
                <th className="payment-input-cell">이번 처리액</th>
              </tr>
            </thead>
            <tbody>
              {status.rows.map((row) => {
                const key = row.payment_key ?? "";
                const selected = Boolean(key && hasOwn(allocations, key));
                return (
                  <tr
                    key={row.id}
                    className={[
                      row.remaining_amount <= 0 ? "paid-row" : "",
                      row.is_deferred ? "deferred-row" : "",
                      row.is_carried_over ? "carried-row" : "",
                    ].filter(Boolean).join(" ")}
                  >
                    <td className="select-cell">
                      <input
                        type="checkbox"
                        checked={selected}
                        disabled={
                          !key ||
                          row.is_deferred ||
                          row.remaining_amount <= 0 ||
                          !status.immediate_allowed ||
                          (isDiscountMode && row.is_toll)
                        }
                        onChange={(event) => onSelect(row, event.target.checked)}
                      />
                    </td>
                    <td className="date">{row.is_carried_over ? "" : row.date_label ?? ""}</td>
                    <td>
                      {displayEntryTitle(row)}
                      {row.is_transport ? <span className="transport-badge">교통</span> : null}
                      {row.is_toll ? <span className="toll-badge">통행료</span> : null}
                      {row.is_deferred ? <span className="deferred-badge">다음 달 이월 예정</span> : null}
                      {row.is_toll && !row.is_carried_over && row.remaining_amount > 0 ? (
                        <button
                          type="button"
                          className="inline-action"
                          disabled={isBusy || !status.immediate_allowed}
                          onClick={() => onTollDeferral(row, !row.is_deferred)}
                        >
                          {row.is_deferred ? "이번 달에 처리" : "이월"}
                        </button>
                      ) : null}
                    </td>
                    <td className="amount">{formatWon(row.original_amount)}</td>
                    <td className="amount">{formatWon(row.immediate_paid_amount)}</td>
                    <td className="amount">{formatWon(row.discount_amount)}</td>
                    <td className="amount">{formatWon(row.remaining_amount)}</td>
                    <td className="payment-input-cell">
                      <input
                        value={selected ? allocations[key] : ""}
                        disabled={!selected || row.is_toll}
                        inputMode="numeric"
                        max={row.remaining_amount}
                        onChange={(event) => setAllocations({ ...allocations, [key]: event.target.value })}
                        placeholder="금액"
                      />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        ) : (
          <p className="empty">직전월 카드 사용내역이 없습니다.</p>
        )}
      </section>

      <section className="panel payment-events">
        <div className="panel-header"><h2>당월 결제금액 기록</h2></div>
        {status.events.length ? (
          <table>
            <thead><tr><th>날짜</th><th>종류</th><th className="amount">금액</th><th className="action-cell">취소</th></tr></thead>
            <tbody>
              {status.events.map((event) => (
                <tr key={event.id}>
                  <td className="date">{formatDateLabel(event.event_date)}</td>
                  <td>{event.event_type === "discount" ? "할인액" : "즉시결제"}</td>
                  <td className="amount">{formatWon(event.total_amount)}</td>
                  <td className="action-cell"><button type="button" className="danger" onClick={() => onDeleteEvent(event.id)}>취소</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <p className="empty">이번 달 결제 또는 할인 기록이 없습니다.</p>}
      </section>
    </section>
  );
}

function PanelAppendForm({
  isBusy,
  panelType,
  panelForm,
  setPanelForm,
  handlePanelSubmit,
}: {
  isBusy: boolean;
  panelType: PanelType;
  panelForm: { panel_type: PanelType; title: string; amount: string; dueDay: string };
  setPanelForm: (value: { panel_type: PanelType; title: string; amount: string; dueDay: string }) => void;
  handlePanelSubmit: (event: FormEvent, panelType: PanelType) => Promise<void>;
}) {
  return (
    <form
      className="panel-form"
      onSubmit={(event) => void handlePanelSubmit(event, panelType)}
    >
      <input
        value={panelForm.panel_type === panelType ? panelForm.title : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: event.target.value,
            amount: panelForm.amount,
            dueDay: panelForm.dueDay,
          })
        }
        placeholder="적요"
      />
      <input
        value={panelForm.panel_type === panelType ? panelForm.amount : ""}
        onChange={(event) =>
          setPanelForm({
            panel_type: panelType,
            title: panelForm.title,
            amount: event.target.value,
            dueDay: panelForm.dueDay,
          })
        }
        inputMode="numeric"
        placeholder="금액"
      />
      <button type="submit" disabled={isBusy}>
        추가
      </button>
    </form>
  );
}

function PlannedTable({
  entries,
  emptyText,
  onConfirm,
  onDelete,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  onConfirm: (entry: LedgerEntry) => void;
  onDelete: (entry: LedgerEntry) => void;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>결제일</th>
          <th>적요</th>
          <th className="amount">금액</th>
          <th className="action-cell">확인</th>
          <th className="action-cell">삭제</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id}>
            <td className="date">{entry.due_day ? `매월 ${entry.due_day}일` : "날짜 없음"}</td>
            <td>{displayEntryTitle(entry)}</td>
            <td className="amount">{formatWon(entry.amount_value)}</td>
            <td className="action-cell">
              <button type="button" onClick={() => onConfirm(entry)}>
                확인
              </button>
            </td>
            <td className="action-cell">
              <button type="button" className="danger" onClick={() => onDelete(entry)}>
                삭제
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CashFlowPanel({
  rows,
  form,
  setForm,
  onSubmit,
  onDelete,
  isBusy,
}: {
  rows: CashFlow[];
  form: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean };
  setForm: (value: { occurredOn: string; direction: string; title: string; amount: string; isPrimaryIncome: boolean }) => void;
  onSubmit: (event: FormEvent) => Promise<void>;
  onDelete: (flow: CashFlow) => void;
  isBusy: boolean;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>현금흐름</h2>
        <span>{formatWon(sumCashFlows(rows))}</span>
      </div>
      {rows.length ? (
        <table>
          <thead>
            <tr>
              <th>날짜</th>
              <th>적요</th>
              <th className="amount">금액</th>
              <th className="action-cell">삭제</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="date">{formatDateLabel(row.occurred_on)}</td>
                <td>{row.title}{row.is_primary_income ? <span className="primary-income-badge">주 수입</span> : null}</td>
                <td className={row.amount_value < 0 ? "amount negative" : "amount positive"}>
                  {formatWon(row.amount_value)}
                </td>
                <td className="action-cell">
                  <button type="button" onClick={() => onDelete(row)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">현금 입출금 기록이 없습니다.</p>
      )}
      <form className="cash-flow-form" onSubmit={(event) => void onSubmit(event)}>
        <input
          type="date"
          value={form.occurredOn}
          onChange={(event) => setForm({ ...form, occurredOn: event.target.value })}
        />
        <select
          value={form.direction}
          onChange={(event) => setForm({ ...form, direction: event.target.value })}
        >
          <option value="in">입금</option>
          <option value="out">출금</option>
        </select>
        <input
          value={form.title}
          onChange={(event) => setForm({ ...form, title: event.target.value })}
          placeholder="적요"
        />
        <input
          value={form.amount}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
          inputMode="numeric"
          placeholder="금액"
        />
        <label className="check-label">
          <input
            type="checkbox"
            checked={form.isPrimaryIncome}
            disabled={form.direction !== "in"}
            onChange={(event) => setForm({ ...form, isPrimaryIncome: event.target.checked })}
          />
          주 수입
        </label>
        <button type="submit" disabled={isBusy}>
          추가
        </button>
      </form>
    </section>
  );
}

function HistoryPanel({
  months,
  selectedMonth,
  setSelectedMonth,
  entries,
  pendingCategoryChanges,
  onCategoryChange,
}: {
  months: string[];
  selectedMonth: string;
  setSelectedMonth: (month: string) => void;
  entries: LedgerEntry[];
  pendingCategoryChanges: Record<number, SpendingCategory | null>;
  onCategoryChange: (entry: LedgerEntry, category: SpendingCategory | null) => void;
}) {
  return (
    <section className="panel history-panel">
      <div className="panel-header history-header">
        <div>
          <h2>월별 기록</h2>
          <p>{entries.length ? `${entries.length}개 항목` : "구조화된 기록이 없습니다."}</p>
        </div>
        <div className="history-controls">
          <select value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)}>
            {months.map((month) => (
              <option key={month} value={month}>
                {formatMonthLabel(month)}
              </option>
            ))}
          </select>
          <span>{formatWon(sumAmounts(entries))}</span>
        </div>
      </div>
      <EntryTable
        entries={entries}
        emptyText="이 달의 구조화된 기록이 없습니다."
        pendingCategoryChanges={pendingCategoryChanges}
        onCategoryChange={onCategoryChange}
      />
    </section>
  );
}

function EntryTable({
  entries,
  emptyText,
  pendingCategoryChanges = {},
  onCategoryChange,
  onDelete,
}: {
  entries: LedgerEntry[];
  emptyText: string;
  pendingCategoryChanges?: Record<number, SpendingCategory | null>;
  onCategoryChange?: (entry: LedgerEntry, category: SpendingCategory | null) => void;
  onDelete?: (entry: LedgerEntry) => void;
}) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>날짜</th>
          <th>사용처</th>
          <th>사용항목</th>
          {onCategoryChange ? <th className="category-cell">분류</th> : null}
          <th className="amount">금액</th>
          {onDelete ? <th className="action-cell">삭제</th> : null}
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => {
          const selectedCategory = hasOwn(pendingCategoryChanges, entry.id)
            ? pendingCategoryChanges[entry.id]
            : entry.spending_category;
          return (
            <tr key={entry.id}>
              <td className="date">{entry.date_label ?? entry.group_label ?? ""}</td>
              <td>{entry.usage_place ?? ""}</td>
              <td>{entry.usage_item ?? displayEntryTitle(entry)}</td>
              {onCategoryChange ? (
                <td className="category-cell">
                  <select
                    value={selectedCategory ?? ""}
                    onChange={(event) =>
                      onCategoryChange(entry, (event.target.value || null) as SpendingCategory | null)
                    }
                  >
                    <option value="">미분류</option>
                    <option value="essential">{categoryLabel("essential")}</option>
                    <option value="questionable">{categoryLabel("questionable")}</option>
                  </select>
                </td>
              ) : null}
              <td className="amount">{formatWon(entry.amount_value)}</td>
              {onDelete ? (
                <td className="action-cell">
                  <button type="button" className="danger" onClick={() => onDelete(entry)}>
                    삭제
                  </button>
                </td>
              ) : null}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function PanelTable({
  title,
  rows,
  onConfirmFrozen,
  onDelete,
  onReset,
  onComplete,
  categoryForPanel,
  form,
}: {
  title: string;
  rows: MonthlyPanel[];
  onConfirmFrozen?: (panel: MonthlyPanel) => void;
  onDelete?: (panel: MonthlyPanel) => void;
  onReset?: () => void;
  onComplete?: () => void;
  categoryForPanel?: (panel: MonthlyPanel) => SpendingCategory | null;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="header-actions">
          <span>{formatWon(sumPanelAmounts(rows))}</span>
          {onComplete && rows.length ? (
            <button type="button" onClick={onComplete}>
              일괄 처리 완료
            </button>
          ) : null}
          {onReset && rows.length ? (
            <button type="button" className="danger" onClick={onReset}>
              초기화
            </button>
          ) : null}
        </div>
      </div>
      {rows.length ? (
        <table>
          <thead>
            <tr>
              <th>적요</th>
              {categoryForPanel ? <th className="category-cell">자동 분류</th> : null}
              <th className="amount">금액</th>
              {onConfirmFrozen ? <th className="action-cell">확인</th> : null}
              {onDelete ? <th className="action-cell">삭제</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>
                  {row.title}
                </td>
                {categoryForPanel ? (
                  <td className="category-cell">{categoryLabel(categoryForPanel(row))}</td>
                ) : null}
                <td className="amount">{formatWon(row.amount_value)}</td>
                {onConfirmFrozen ? (
                  <td className="action-cell">
                    <button type="button" onClick={() => onConfirmFrozen(row)}>
                      확인
                    </button>
                  </td>
                ) : null}
                {onDelete ? (
                  <td className="action-cell">
                    <button type="button" className="danger" onClick={() => onDelete(row)}>
                      삭제
                    </button>
                  </td>
                ) : null}
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">항목이 없습니다.</p>
      )}
      {form}
    </section>
  );
}

function InstallmentTable({
  rows,
  onDelete,
  form,
}: {
  rows: Installment[];
  onDelete: (installment: Installment) => void;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>할부</h2>
        <span>{formatWon(sumInstallmentMonthlyAmounts(rows))}</span>
      </div>
      {rows.length ? (
        <table>
          <thead>
            <tr>
              <th>적요</th>
              <th className="amount">할부액</th>
              <th className="amount">수수료율</th>
              <th className="amount">수수료</th>
              <th className="amount">잔여</th>
              <th className="amount">월 납입액</th>
              <th className="action-cell">삭제</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.title}</td>
                <td className="amount">{formatWon(row.principal_amount)}</td>
                <td className="amount">{row.fee_rate.toLocaleString("ko-KR")}%</td>
                <td className="amount">{formatWon(row.fee_amount)}</td>
                <td className="amount">
                  {row.remaining_months}/{row.months}개월
                </td>
                <td className="amount">{formatWon(row.monthly_amount)}</td>
                <td className="action-cell">
                  <button type="button" className="danger" onClick={() => onDelete(row)}>
                    삭제
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">할부 항목이 없습니다.</p>
      )}
      {form}
    </section>
  );
}

function panelLabel(labels: Record<string, string>, type: PanelType): string {
  const meta = panelMeta[type];
  return labels[meta.labelKey] ?? meta.fallback;
}

function isAuthRequiredError(error: unknown): boolean {
  return error instanceof Error && error.message.includes("authentication required");
}

function parseAmount(value: string): number | null {
  const normalized = value.replaceAll(",", "").trim();
  if (!normalized) return null;
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : null;
}

function formatUsageTitle(usagePlace: string, usageItem: string): string {
  if (usagePlace && usageItem) return `[${usagePlace}] ${usageItem}`;
  if (usagePlace) return `[${usagePlace}]`;
  return usageItem;
}

function displayEntryTitle(entry: LedgerEntry): string {
  if (entry.title.startsWith("[이월]")) return entry.title;
  if (entry.usage_place || entry.usage_item) {
    return formatUsageTitle(entry.usage_place ?? "", entry.usage_item ?? "");
  }
  return entry.title;
}

function activeStatItems(
  activePrimaryTab: PrimaryTab,
  activeCurrentTab: CurrentTab,
  expenseEntries: LedgerEntry[],
  _historyEntries: LedgerEntry[],
  panels: MonthlyPanel[],
  pendingCategoryChanges: Record<number, SpendingCategory | null>,
): StatItem[] {
  if (activePrimaryTab === "current" && activeCurrentTab === "claim") {
    return panels
      .filter((panel) => panel.panel_type === "claim")
      .map((panel) => ({
        amount_value: panel.amount_value,
        spending_category: classifyClaimPanel(panel),
      }));
  }
  return expenseEntries.map((entry) => ({
    amount_value: entry.amount_value,
    spending_category: hasOwn(pendingCategoryChanges, entry.id)
      ? pendingCategoryChanges[entry.id]
      : entry.spending_category,
  }));
}

function parseOptionalDay(value: string): number | null {
  const day = Number(value.trim());
  if (!Number.isInteger(day)) return null;
  if (day < 1 || day > 31) return null;
  return day;
}

function nextSortOrder(rows: { sort_order: number }[]): number {
  return rows.reduce((max, row) => Math.max(max, row.sort_order), 0) + 1;
}

function collectEntryMonths(entries: LedgerEntry[], fallbackMonth: string): string[] {
  const months = new Set(entries.map((entry) => entry.entry_date?.slice(0, 7)).filter(Boolean) as string[]);
  months.add(fallbackMonth);
  return [...months].sort((a, b) => b.localeCompare(a));
}

function compareEntriesByDate(a: LedgerEntry, b: LedgerEntry): number {
  const dateCompare = (a.entry_date ?? "").localeCompare(b.entry_date ?? "");
  if (dateCompare !== 0) return dateCompare;
  return a.sort_order - b.sort_order || a.id - b.id;
}

function detectCurrentMonth(entries: LedgerEntry[]): string {
  const dated = entries.find((entry) => entry.entry_date);
  return dated?.entry_date?.slice(0, 7) ?? today.slice(0, 7);
}

function formatDateLabel(value: string): string | null {
  if (!value) return null;
  const [year, month, day] = value.split("-");
  return `${year}.${month}.${day}.`;
}

function formatMonthLabel(value: string): string {
  const [year, month] = value.split("-");
  return `${year}년 ${Number(month)}월`;
}

function previousMonthLastDay(value: string): string {
  const dateValue = new Date(`${value}T00:00:00`);
  dateValue.setDate(0);
  return [
    dateValue.getFullYear(),
    String(dateValue.getMonth() + 1).padStart(2, "0"),
    String(dateValue.getDate()).padStart(2, "0"),
  ].join("-");
}

function previousMonthFirstDay(value: string): string {
  return previousMonthLastDay(value).slice(0, 8) + "01";
}

function sumAmounts(entries: LedgerEntry[]): number {
  return entries.reduce((total, entry) => total + (entry.amount_value ?? 0), 0);
}

function sumPanelAmounts(rows: MonthlyPanel[]): number {
  return rows.reduce((total, row) => total + (row.amount_value ?? 0), 0);
}

function sumCashFlows(rows: CashFlow[]): number {
  return rows.reduce((total, row) => total + row.amount_value, 0);
}

function sumInstallmentMonthlyAmounts(rows: Installment[]): number {
  return rows.reduce((total, row) => total + row.monthly_amount, 0);
}

function sumStatItems(rows: StatItem[]): number {
  return rows.reduce((total, row) => total + (row.amount_value ?? 0), 0);
}

function sumPaymentAllocationInputs(values: Record<string, string>): number {
  return Object.values(values).reduce((total, value) => total + (parseAmount(value) ?? 0), 0);
}

function daysBetween(from: string, to: string): number {
  const start = new Date(`${from}T00:00:00`).getTime();
  const end = new Date(`${to}T00:00:00`).getTime();
  return Math.round((end - start) / 86_400_000);
}

function parseSettingNumber(settings: Settings, key: string, fallback: number): number {
  const parsed = Number(settings[key]);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function formatWon(value: number | null): string {
  return `${Math.round(value ?? 0).toLocaleString("ko-KR")}원`;
}

function formatAuditTimestamp(value: string): string {
  const parsed = new Date(`${value.replace(" ", "T")}Z`);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString("ko-KR", { hour12: false });
}
