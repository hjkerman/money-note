import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  CashFlow,
  Installment,
  LedgerEntry,
  MonthlyPanel,
  Settings,
  SpendingCategory,
  Summary,
  appendPlannedEntry,
  closeCurrentMonth,
  confirmFrozenPanel,
  confirmPlannedEntry,
  createCashFlow,
  createEntry,
  createExport,
  createInstallment,
  createPanel,
  deleteEntry,
  deleteCashFlow,
  deleteInstallment,
  deletePanel,
  deletePanelsByType,
  deletePlannedEntry,
  fetchCashFlows,
  fetchArchiveEntries,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchInstallments,
  fetchLabels,
  fetchMe,
  fetchSettings,
  fetchSummary,
  latestExportUrl,
  login,
  logout,
  updateEntry,
} from "./api";
import { categoryLabel, classifyClaimPanel, creditUsageTone, spendingStatTones } from "./judgment";

type PanelType = MonthlyPanel["panel_type"];
type PrimaryTab = "current" | "fixed" | "frozen" | "cash";
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
const hasOwn = (record: Record<number, unknown>, key: number) => Object.prototype.hasOwnProperty.call(record, key);

export function App() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [archiveEntries, setArchiveEntries] = useState<LedgerEntry[]>([]);
  const [panels, setPanels] = useState<MonthlyPanel[]>([]);
  const [cashFlows, setCashFlows] = useState<CashFlow[]>([]);
  const [installments, setInstallments] = useState<Installment[]>([]);
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
  const [pendingCategoryChanges, setPendingCategoryChanges] = useState<Record<number, SpendingCategory | null>>({});

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
      ] = await Promise.all([
        fetchCurrentEntries(),
        fetchArchiveEntries(),
        fetchCurrentPanels(),
        fetchSummary(),
        fetchLabels(),
        fetchCashFlows(),
        fetchSettings(),
        fetchInstallments(),
      ]);
      setEntries(nextEntries);
      setArchiveEntries(nextArchiveEntries);
      setPanels(nextPanels);
      setSummary(nextSummary);
      setLabels(nextLabels);
      setCashFlows(nextCashFlows);
      setSettings(nextSettings);
      setInstallments(nextInstallments);
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
      setStatus("로그인 완료");
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
      await createEntry({
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
      setStatus("당월 기록 추가 완료");
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
        month: currentMonth,
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

  async function handlePanelReset(panelType: PanelType) {
    const targetPanels = panels.filter((panel) => panel.panel_type === panelType);
    if (!targetPanels.length) return;
    const confirmed = window.confirm(`${panelLabel(labels, panelType)} 항목 ${targetPanels.length}개를 전부 초기화할까요?`);
    if (!confirmed) return;
    await withRefresh(async () => {
      await deletePanelsByType(panelType);
      setStatus(`${panelLabel(labels, panelType)} 초기화 완료`);
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

  async function handleCloseMonth() {
    const confirmed = window.confirm("카드 정기결제를 제외한 당월 기록을 전체 기록으로 넘길까요?");
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await closeCurrentMonth();
      setStatus(`월마감 완료: ${result.archived}개 archive`);
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
          <button type="button" className="danger" onClick={() => void handleCloseMonth()} disabled={isBusy}>
            월마감
          </button>
          <button type="button" onClick={() => void handleLogout()} disabled={isBusy}>
            로그아웃
          </button>
        </div>
      </header>

      <section className="statusline">{status}</section>

      <SummaryPanel summary={summary} labels={labels} />

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
                      categoryForPanel={tab === "claim" ? classifyClaimPanel : undefined}
                      onDelete={(panel) => void handlePanelDelete(panel)}
                      onReset={tab === "claim" || tab === "settlement" ? () => void handlePanelReset(tab) : undefined}
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

function SummaryPanel({ summary, labels }: { summary: Summary | null; labels: Record<string, string> }) {
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
        <dl>
          {rows.map(([label, value]) => (
            <div key={label} className={label === (labels.summary_next_month_liquidity_label ?? "익월 유동성") ? "total" : ""}>
              <dt>{label}</dt>
              <dd>{formatWon(value as number)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="empty">요약을 불러오는 중입니다.</p>
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
  form: { occurredOn: string; direction: string; title: string; amount: string };
  setForm: (value: { occurredOn: string; direction: string; title: string; amount: string }) => void;
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
                <td>{row.title}</td>
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
          <th>적요</th>
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
              <td>{displayEntryTitle(entry)}</td>
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
  categoryForPanel,
  form,
}: {
  title: string;
  rows: MonthlyPanel[];
  onConfirmFrozen?: (panel: MonthlyPanel) => void;
  onDelete?: (panel: MonthlyPanel) => void;
  onReset?: () => void;
  categoryForPanel?: (panel: MonthlyPanel) => SpendingCategory | null;
  form?: ReactNode;
}) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <div className="header-actions">
          <span>{formatWon(sumPanelAmounts(rows))}</span>
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

function parseSettingNumber(settings: Settings, key: string, fallback: number): number {
  const parsed = Number(settings[key]);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function formatWon(value: number | null): string {
  return `${Math.round(value ?? 0).toLocaleString("ko-KR")}원`;
}
