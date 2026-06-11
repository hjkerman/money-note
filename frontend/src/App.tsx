import { useEffect, useMemo, useState } from "react";
import {
  AuditLog,
  CardDiscountMonth,
  CardPaymentStatus,
  CashFlow,
  Installment,
  JudgmentState,
  LedgerEntry,
  MonthlyPanel,
  MonthCloseStatus,
  Settings,
  Summary,
} from "./api";
import { useAuthSession } from "./hooks/useAuthSession";
import { useCardPaymentHandlers } from "./hooks/useCardPaymentHandlers";
import { useCashFlowHandlers } from "./hooks/useCashFlowHandlers";
import { useEntryHandlers } from "./hooks/useEntryHandlers";
import { useInstallmentHandlers } from "./hooks/useInstallmentHandlers";
import { useLedgerSnapshot } from "./hooks/useLedgerSnapshot";
import { useModalState } from "./hooks/useModalState";
import { useMoneyNoteForms } from "./hooks/useMoneyNoteForms";
import { usePanelHandlers } from "./hooks/usePanelHandlers";
import { useSettingsHandlers } from "./hooks/useSettingsHandlers";
import { CurrentTab, PrimaryTab } from "./types";
import { AppHeader } from "./components/AppHeader";
import { AppShell } from "./components/AppShell";
import { AppStatusArea } from "./components/AppStatusArea";
import { CardPaymentView } from "./components/CardPaymentView";
import { CurrentMonthView } from "./components/CurrentMonthView";
import { SummaryPanel } from "./components/Insights";
import { InitialLoadingView, LoginView } from "./components/LoginView";
import { CashFlowView, FixedPanelView, FrozenPanelView } from "./components/MonthlyPanelsView";
import { SettingsModal } from "./components/SettingsModal";
import { StatsModal } from "./components/StatsModal";
import {
  activeStatItems,
  collectEntryMonths,
  compareEntriesByDate,
  detectCurrentMonth,
  formatIntegerSetting,
  formatWon,
  isAuthRequiredError,
  panelLabel,
  sumAmounts,
  sumCashFlows,
  sumInstallmentMonthlyAmounts,
  sumPanelAmounts,
  sumPanelNetAmounts,
} from "./utils";

export function App() {
  const { loadLedgerSnapshot } = useLedgerSnapshot();
  const {
    activeCurrentTab,
    activePrimaryTab,
    selectedHistoryMonth,
    setActiveCurrentTab,
    setActivePrimaryTab,
    setSelectedHistoryMonth,
    setShowAuditLogs,
    setShowSettings,
    setShowStats,
    showAuditLogs,
    showSettings,
    showStats,
  } = useModalState();
  const {
    cashFlowForm,
    expenseForm,
    installmentForm,
    lateEntryForm,
    loginForm,
    panelForm,
    passwordForm,
    plannedForm,
    resetPassword,
    setCashFlowForm,
    setExpenseForm,
    setInstallmentForm,
    setLateEntryForm,
    setLoginForm,
    setPanelForm,
    setPasswordForm,
    setPlannedForm,
    setResetPassword,
  } = useMoneyNoteForms();
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
  const [isBusy, setIsBusy] = useState(false);
  const [interestExpenseInput, setInterestExpenseInput] = useState("");
  const [scheduledIncomeInput, setScheduledIncomeInput] = useState("");
  const [familyCardLimitInput, setFamilyCardLimitInput] = useState("");
  const [ownerCardLast4Input, setOwnerCardLast4Input] = useState("");
  const [familyCardLast4Input, setFamilyCardLast4Input] = useState("");
  const [paymentAllocations, setPaymentAllocations] = useState<Record<string, string>>({});
  const [paymentBudget, setPaymentBudget] = useState("");
  const {
    authChecked,
    authUser,
    checkAuth,
    handleAuthRequired,
    handleLogin,
    handleLogout,
    setAuthUser,
  } = useAuthSession({
    loginForm,
    onLogoutClear: clearLedgerState,
    onRefresh: refresh,
    setIsBusy,
    setLoginForm,
    setStatus,
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
      id: "family_card",
      label: panelLabel(labels, "family_card"),
      total: sumPanelNetAmounts(panels.filter((panel) => panel.panel_type === "family_card"), familyDiscountMonth?.policy),
    },
    {
      id: "installments",
      label: "할부",
      total: sumInstallmentMonthlyAmounts(installments),
    },
  ];
  const {
    handleCategoryChange,
    handleEntryDelete,
    handleExpenseSubmit,
    handlePlannedConfirm,
    handlePlannedDelete,
    handlePlannedSubmit,
  } = useEntryHandlers({
    entries,
    expenseForm,
    plannedForm,
    setExpenseForm,
    setPlannedForm,
    setStatus,
    withRefresh,
  });
  const {
    handlePanelComplete,
    handlePanelDelete,
    handlePanelDiscount,
    handlePanelDiscountClear,
    handlePanelShare,
    handlePanelSubmit,
  } = usePanelHandlers({
    familyDiscountPolicy: familyDiscountMonth?.policy,
    labels,
    month: monthCloseStatus?.calendar_month,
    ownerDiscountPolicy: ownerDiscountMonth?.policy,
    panelForm,
    panels,
    setPanelForm,
    setStatus,
    withRefresh,
  });
  const { handleCashFlowDelete, handleCashFlowSubmit } = useCashFlowHandlers({
    cashFlowForm,
    cashFlows,
    setCashFlowForm,
    setStatus,
    withRefresh,
  });
  const { handleInstallmentDelete, handleInstallmentSubmit } = useInstallmentHandlers({
    currentMonth,
    installmentForm,
    installments,
    setInstallmentForm,
    setStatus,
    withRefresh,
  });
  const {
    handleAutoAllocate,
    handleCardPaymentEventDelete,
    handleCardPaymentRowDelete,
    handleCardPaymentSubmit,
    handleCurrentEntryDiscount,
    handleCurrentEntryDiscountClear,
    handleDiscountPolicyChange,
    handleLateEntrySubmit,
    handleLiquidityResetAcknowledgement,
    handlePaymentSelection,
    handleTollDeferral,
  } = useCardPaymentHandlers({
    cardPayments,
    lateEntryForm,
    ownerDiscountPolicy: ownerDiscountMonth?.policy,
    paymentAllocations,
    paymentBudget,
    setLateEntryForm,
    setPaymentAllocations,
    setStatus,
    summary,
    withRefresh,
  });
  const {
    handleAuditLogClear,
    handleAuditLogToggle,
    handleCardLast4Save,
    handleCloseMonth,
    handleFamilyCardLimitSave,
    handleInterestExpenseSave,
    handleLedgerReset,
    handlePasswordChange,
    handleScheduledIncomeSave,
    handleSharePinSet,
    handleSnapshotRestore,
  } = useSettingsHandlers({
    familyCardLimitInput,
    interestExpenseInput,
    monthCloseStatus,
    passwordForm,
    resetPassword,
    scheduledIncomeInput,
    setAuditLogs,
    setAuthUser,
    setFamilyCardLimitInput,
    setInterestExpenseInput,
    setIsBusy,
    setPasswordForm,
    setPaymentAllocations,
    setResetPassword,
    setScheduledIncomeInput,
    setShowAuditLogs,
    setStatus,
    showAuditLogs,
    withRefresh,
  });

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
      setFamilyCardLimitInput(formatIntegerSetting(snapshot.settings.family_card_limit));
      setOwnerCardLast4Input(snapshot.settings.owner_card_last4 ?? "");
      setFamilyCardLast4Input(snapshot.settings.family_card_last4 ?? "");
      setInstallments(snapshot.installments);
      setCardPayments(snapshot.cardPayments);
      setMonthCloseStatus(snapshot.monthCloseStatus);
      setOwnerDiscountMonth(snapshot.ownerDiscountMonth);
      setFamilyDiscountMonth(snapshot.familyDiscountMonth);
      setStatus("동기화 완료");
    } catch (error) {
      if (isAuthRequiredError(error)) {
        handleAuthRequired();
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

  function clearLedgerState() {
    setEntries([]);
    setArchiveEntries([]);
    setPanels([]);
    setCashFlows([]);
    setCardPayments(null);
    setSummary(null);
    setLabels({});
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
    return <InitialLoadingView />;
  }

  if (!authUser) {
    return (
      <LoginView
        isBusy={isBusy}
        loginForm={loginForm}
        onLogin={(event) => void handleLogin(event)}
        setLoginForm={setLoginForm}
        status={status}
      />
    );
  }

  return (
    <AppShell
      header={
        <AppHeader
          currentMonth={currentMonth}
          isBusy={isBusy}
          monthCloseStatus={monthCloseStatus}
          onAuditLogToggle={() => void handleAuditLogToggle()}
          onCloseMonth={() => void handleCloseMonth()}
          onLogout={() => void handleLogout()}
          onOpenSettings={() => setShowSettings(true)}
          onShowStatsToggle={() => setShowStats(!showStats)}
          showStats={showStats}
        />
      }
      settings={
        showSettings ? (
          <SettingsModal
            familyCardLast4Input={familyCardLast4Input}
            familyCardLimitInput={familyCardLimitInput}
            interestExpenseInput={interestExpenseInput}
            isBusy={isBusy}
            onCardLast4Save={(key, value) => void handleCardLast4Save(key, value)}
            onClose={() => setShowSettings(false)}
            onFamilyCardLimitSave={() => void handleFamilyCardLimitSave()}
            onInterestExpenseSave={() => void handleInterestExpenseSave()}
            onLedgerReset={() => void handleLedgerReset()}
            onPasswordChange={() => void handlePasswordChange()}
            onScheduledIncomeSave={() => void handleScheduledIncomeSave()}
            onSharePinSet={() => void handleSharePinSet()}
            onSnapshotRestore={(file) => void handleSnapshotRestore(file)}
            ownerCardLast4Input={ownerCardLast4Input}
            passwordForm={passwordForm}
            resetPassword={resetPassword}
            scheduledIncomeInput={scheduledIncomeInput}
            setFamilyCardLast4Input={setFamilyCardLast4Input}
            setFamilyCardLimitInput={setFamilyCardLimitInput}
            setInterestExpenseInput={setInterestExpenseInput}
            setOwnerCardLast4Input={setOwnerCardLast4Input}
            setPasswordForm={setPasswordForm}
            setResetPassword={setResetPassword}
            setScheduledIncomeInput={setScheduledIncomeInput}
          />
        ) : null
      }
    >
      <AppStatusArea
        auditLogs={auditLogs}
        authUser={authUser}
        isBusy={isBusy}
        monthCloseStatus={monthCloseStatus}
        onAuditLogClear={() => void handleAuditLogClear()}
        onCloseMonth={() => void handleCloseMonth()}
        onSharePinSet={() => void handleSharePinSet()}
        showAuditLogs={showAuditLogs}
        status={status}
      />
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

          <CurrentMonthView
              active={activePrimaryTab === "current"}
              activeCurrentTab={activeCurrentTab}
              currentSubTabs={currentSubTabs}
              expenseEntries={expenseEntries}
              expenseForm={expenseForm}
              familyDiscountMonth={familyDiscountMonth}
              handleCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
              handleCurrentEntryDiscount={(entry) => void handleCurrentEntryDiscount(entry)}
              handleCurrentEntryDiscountClear={(entry) => void handleCurrentEntryDiscountClear(entry)}
              handleDiscountPolicyChange={(scope, month, policy) => void handleDiscountPolicyChange(scope, month, policy)}
              handleEntryDelete={(entry) => void handleEntryDelete(entry)}
              handleExpenseSubmit={(event) => void handleExpenseSubmit(event)}
              handleInstallmentDelete={(installment) => void handleInstallmentDelete(installment)}
              handleInstallmentSubmit={(event) => void handleInstallmentSubmit(event)}
              handlePanelComplete={(panelType) => void handlePanelComplete(panelType)}
              handlePanelDelete={(panel) => void handlePanelDelete(panel)}
              handlePanelDiscount={(panel) => void handlePanelDiscount(panel)}
              handlePanelDiscountClear={(panel) => void handlePanelDiscountClear(panel)}
              handlePanelShare={(panelType) => void handlePanelShare(panelType)}
              handlePanelSubmit={handlePanelSubmit}
              installmentForm={installmentForm}
              installments={installments}
              isBusy={isBusy}
              judgment={judgment}
              labels={labels}
              ownerDiscountMonth={ownerDiscountMonth}
              panelForm={panelForm}
              panels={panels}
              setActiveCurrentTab={setActiveCurrentTab}
              setExpenseForm={setExpenseForm}
              setInstallmentForm={setInstallmentForm}
              setPanelForm={setPanelForm}
              settings={settings}
            />

          <FixedPanelView
              active={activePrimaryTab === "fixed"}
              handlePanelDelete={(panel) => void handlePanelDelete(panel)}
              handlePanelSubmit={handlePanelSubmit}
              handlePlannedConfirm={(entry) => void handlePlannedConfirm(entry)}
              handlePlannedDelete={(entry) => void handlePlannedDelete(entry)}
              handlePlannedSubmit={(event) => void handlePlannedSubmit(event)}
              isBusy={isBusy}
              labels={labels}
              panelForm={panelForm}
              panels={panels}
              plannedEntries={plannedEntries}
              plannedForm={plannedForm}
              setPanelForm={setPanelForm}
              setPlannedForm={setPlannedForm}
            />

          <CardPaymentView
              active={activePrimaryTab === "payment"}
              cardPayments={cardPayments}
              handleAutoAllocate={handleAutoAllocate}
              handleCardPaymentEventDelete={(eventId) => void handleCardPaymentEventDelete(eventId)}
              handleCardPaymentRowDelete={(row) => void handleCardPaymentRowDelete(row)}
              handleCardPaymentSubmit={() => void handleCardPaymentSubmit()}
              handleDiscountPolicyChange={(scope, month, policy) => void handleDiscountPolicyChange(scope, month, policy)}
              handleLateEntrySubmit={handleLateEntrySubmit}
              handleLiquidityResetAcknowledgement={() => void handleLiquidityResetAcknowledgement()}
              handlePaymentSelection={(row, selected) => void handlePaymentSelection(row, selected)}
              handleTollDeferral={(row, defer) => void handleTollDeferral(row, defer)}
              isBusy={isBusy}
              judgment={judgment}
              lateEntryForm={lateEntryForm}
              paymentAllocations={paymentAllocations}
              paymentBudget={paymentBudget}
              setLateEntryForm={setLateEntryForm}
              setPaymentAllocations={setPaymentAllocations}
              setPaymentBudget={setPaymentBudget}
              settings={settings}
              summary={summary}
            />

          <FrozenPanelView
              active={activePrimaryTab === "frozen"}
              handlePanelDelete={(panel) => void handlePanelDelete(panel)}
              handlePanelSubmit={handlePanelSubmit}
              isBusy={isBusy}
              labels={labels}
              panelForm={panelForm}
              panels={panels}
              setPanelForm={setPanelForm}
            />

          <CashFlowView
              active={activePrimaryTab === "cash"}
              cashFlowForm={cashFlowForm}
              cashFlows={cashFlows}
              handleCashFlowDelete={(flow) => void handleCashFlowDelete(flow)}
              handleCashFlowSubmit={handleCashFlowSubmit}
              isBusy={isBusy}
              setCashFlowForm={setCashFlowForm}
            />

        </div>
      </section>

    </AppShell>
  );
}
