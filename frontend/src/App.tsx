import { useEffect } from "react";
import { useAuthSession } from "./hooks/useAuthSession";
import { useAppDerivedState } from "./hooks/useAppDerivedState";
import { useAppRefresh } from "./hooks/useAppRefresh";
import { useCardPaymentHandlers } from "./hooks/useCardPaymentHandlers";
import { useCashFlowHandlers } from "./hooks/useCashFlowHandlers";
import { useEntryHandlers } from "./hooks/useEntryHandlers";
import { useModalState } from "./hooks/useModalState";
import { useMoneyNoteForms } from "./hooks/useMoneyNoteForms";
import { usePanelHandlers } from "./hooks/usePanelHandlers";
import { useSettingsHandlers } from "./hooks/useSettingsHandlers";
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
import { formatWon } from "./utils";

export function App() {
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
    lateEntryForm,
    loginForm,
    panelForm,
    passwordForm,
    plannedForm,
    resetPassword,
    setCashFlowForm,
    setExpenseForm,
    setLateEntryForm,
    setLoginForm,
    setPanelForm,
    setPasswordForm,
    setPlannedForm,
    setResetPassword,
  } = useMoneyNoteForms();
  const {
    archiveEntries,
    auditLogs,
    cardLimitInput,
    cardPayments,
    cashFlows,
    confirmedPlannedEntries,
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
  } = useAppRefresh({
    setCashFlowForm,
    setExpenseForm,
    setLateEntryForm,
    setPanelForm,
  });
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
  const {
    currentMonth,
    currentSubTabs,
    expenseEntries,
    historyEntries,
    historyMonths,
    plannedEntries,
    primaryTabs,
    statsItems,
  } = useAppDerivedState({
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
  });
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
    handlePanelNetAmountEdit,
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
  const {
    handleAutoAllocate,
    handleCardPaymentDiscountToggle,
    handleCardPaymentEventDelete,
    handleCardPaymentRowDelete,
    handleCardPaymentSubmit,
    handleCurrentEntryDiscount,
    handleCurrentEntryDiscountClear,
    handleCurrentEntryNetAmountEdit,
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
    handleApkDownload,
    handleAuditLogClear,
    handleAuditLogToggle,
    handleCardLast4Save,
    handleCloseMonth,
    handleCardLimitSave,
    handleInterestExpenseSave,
    handleLedgerReset,
    handleOperationStatsLoad,
    handlePasswordChange,
    handlePreRestoreDelete,
    handlePreRestoreDeleteAll,
    handlePreRestoreList,
    handlePreRestoreRestore,
    handleScheduledIncomeSave,
    handleSharePinSet,
    handleSnapshotDownload,
    handleSnapshotRestore,
  } = useSettingsHandlers({
    cardLimitInput,
    interestExpenseInput,
    monthCloseStatus,
    passwordForm,
    resetPassword,
    scheduledIncomeInput,
    setAuditLogs,
    setAuthUser,
    setCardLimitInput,
    setInterestExpenseInput,
    setIsBusy,
    setOperationStats,
    setPasswordForm,
    setPaymentAllocations,
    setPreRestoreBackups,
    setResetPassword,
    setScheduledIncomeInput,
    setShowAuditLogs,
    setStatus,
    showAuditLogs,
    withRefresh,
  });

  useEffect(() => {
    void checkAuth();
  }, []);

  useEffect(() => {
    registerAuthRequiredHandler(handleAuthRequired);
  }, [handleAuthRequired, registerAuthRequiredHandler]);

  useEffect(() => {
    if (showSettings) void handleOperationStatsLoad();
  }, [showSettings]);

  useEffect(() => {
    if (!showStats) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setShowStats(false);
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [showStats]);

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
              cardLimitInput={cardLimitInput}
              interestExpenseInput={interestExpenseInput}
              isBusy={isBusy}
              onApkDownload={() => void handleApkDownload()}
              onCardLast4Save={(key, value) => void handleCardLast4Save(key, value)}
            onClose={() => setShowSettings(false)}
            onCardLimitSave={() => void handleCardLimitSave()}
            onInterestExpenseSave={() => void handleInterestExpenseSave()}
              onLedgerReset={() => void handleLedgerReset()}
              onOperationStatsLoad={() => void handleOperationStatsLoad()}
              onPasswordChange={() => void handlePasswordChange()}
            onPreRestoreDelete={(filename) => void handlePreRestoreDelete(filename)}
            onPreRestoreDeleteAll={() => void handlePreRestoreDeleteAll()}
            onPreRestoreList={() => void handlePreRestoreList()}
            onPreRestoreRestore={(filename) => void handlePreRestoreRestore(filename)}
            onScheduledIncomeSave={() => void handleScheduledIncomeSave()}
            onSharePinSet={() => void handleSharePinSet()}
            onSnapshotDownload={() => void handleSnapshotDownload()}
            onSnapshotRestore={(file) => void handleSnapshotRestore(file)}
            ownerCardLast4Input={ownerCardLast4Input}
            operationStats={operationStats}
            passwordForm={passwordForm}
            preRestoreBackups={preRestoreBackups}
            resetPassword={resetPassword}
            scheduledIncomeInput={scheduledIncomeInput}
            setFamilyCardLast4Input={setFamilyCardLast4Input}
            setCardLimitInput={setCardLimitInput}
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
              currentMonth={currentMonth}
              currentSubTabs={currentSubTabs}
              expenseEntries={expenseEntries}
              expenseForm={expenseForm}
              familyDiscountMonth={familyDiscountMonth}
              handleCategoryChange={(entry, category) => void handleCategoryChange(entry, category)}
              handleCurrentEntryDiscount={(entry) => void handleCurrentEntryDiscount(entry)}
              handleCurrentEntryDiscountClear={(entry) => void handleCurrentEntryDiscountClear(entry)}
              handleCurrentEntryNetAmountEdit={(entry) => void handleCurrentEntryNetAmountEdit(entry)}
              handleDiscountPolicyChange={(scope, month, policy) => void handleDiscountPolicyChange(scope, month, policy)}
              handleEntryDelete={(entry) => void handleEntryDelete(entry)}
              handleExpenseSubmit={(event) => void handleExpenseSubmit(event)}
              handlePanelComplete={(panelType) => void handlePanelComplete(panelType)}
              handlePanelDelete={(panel) => void handlePanelDelete(panel)}
              handlePanelDiscount={(panel) => void handlePanelDiscount(panel)}
              handlePanelDiscountClear={(panel) => void handlePanelDiscountClear(panel)}
              handlePanelNetAmountEdit={(panel) => void handlePanelNetAmountEdit(panel)}
              handlePanelShare={(panelType) => void handlePanelShare(panelType)}
              handlePanelSubmit={handlePanelSubmit}
              isBusy={isBusy}
              judgment={judgment}
              labels={labels}
              ownerDiscountMonth={ownerDiscountMonth}
              panelForm={panelForm}
              panels={panels}
              setActiveCurrentTab={setActiveCurrentTab}
              setExpenseForm={setExpenseForm}
              setPanelForm={setPanelForm}
              settings={settings}
            />

          <FixedPanelView
              active={activePrimaryTab === "fixed"}
              currentMonth={currentMonth}
              handlePanelDelete={(panel) => void handlePanelDelete(panel)}
              handlePanelSubmit={handlePanelSubmit}
              handlePlannedConfirm={(entry, entryDate) => void handlePlannedConfirm(entry, entryDate)}
              handlePlannedDelete={(entry) => void handlePlannedDelete(entry)}
              handlePlannedSubmit={(event) => void handlePlannedSubmit(event)}
              isBusy={isBusy}
              labels={labels}
              panelForm={panelForm}
              panels={panels}
              confirmedPlannedEntries={confirmedPlannedEntries}
              plannedEntries={plannedEntries}
              plannedForm={plannedForm}
              setPanelForm={setPanelForm}
              setPlannedForm={setPlannedForm}
              summary={summary}
            />

          <CardPaymentView
              active={activePrimaryTab === "payment"}
              cardPayments={cardPayments}
              handleAutoAllocate={handleAutoAllocate}
              handleCardPaymentDiscountToggle={(row, exclude) => void handleCardPaymentDiscountToggle(row, exclude)}
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
