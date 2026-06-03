import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  AuthUser,
  LedgerEntry,
  MonthlyPanel,
  Summary,
  appendPlannedEntry,
  closeCurrentMonth,
  createEntry,
  createExport,
  createPanel,
  fetchCurrentEntries,
  fetchCurrentPanels,
  fetchLabels,
  fetchMe,
  fetchSummary,
  latestExportUrl,
  login,
  logout,
} from "./api";

type PanelType = MonthlyPanel["panel_type"];

const panelMeta: Record<PanelType, { labelKey: string; fallback: string }> = {
  fixed: { labelKey: "panel_fixed_title", fallback: "고정지출" },
  frozen: { labelKey: "panel_frozen_title", fallback: "동결" },
  claim: { labelKey: "panel_claim_title", fallback: "청구" },
  settlement: { labelKey: "panel_settlement_title", fallback: "타인정산" },
};

const today = new Date().toISOString().slice(0, 10);

export function App() {
  const [entries, setEntries] = useState<LedgerEntry[]>([]);
  const [panels, setPanels] = useState<MonthlyPanel[]>([]);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("서버와 통신 준비 중");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);
  const [isBusy, setIsBusy] = useState(false);
  const [loginForm, setLoginForm] = useState({ username: "", password: "" });
  const [expenseForm, setExpenseForm] = useState({ date: today, title: "", amount: "" });
  const [plannedForm, setPlannedForm] = useState({ title: "", amount: "" });
  const [panelForm, setPanelForm] = useState<{
    panel_type: PanelType;
    title: string;
    amount: string;
  }>({ panel_type: "fixed", title: "", amount: "" });

  const plannedEntries = entries.filter((entry) => entry.entry_kind === "planned");
  const expenseEntries = entries.filter((entry) => entry.entry_kind !== "planned");
  const currentMonth = useMemo(() => detectCurrentMonth(entries), [entries]);

  async function refresh() {
    setIsBusy(true);
    try {
      const [nextEntries, nextPanels, nextSummary, nextLabels] = await Promise.all([
        fetchCurrentEntries(),
        fetchCurrentPanels(),
        fetchSummary(),
        fetchLabels(),
      ]);
      setEntries(nextEntries);
      setPanels(nextPanels);
      setSummary(nextSummary);
      setLabels(nextLabels);
      setStatus("동기화 완료");
    } catch (error) {
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
    } catch {
      setStatus("로그인이 필요합니다.");
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
      setPanels([]);
      setSummary(null);
      setLabels({});
      setStatus("로그아웃 완료");
    } catch (error) {
      setStatus(`로그아웃 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleExpenseSubmit(event: FormEvent) {
    event.preventDefault();
    if (!expenseForm.title.trim()) return;
    await withRefresh(async () => {
      const dateLabel = formatDateLabel(expenseForm.date);
      await createEntry({
        book_section: "current",
        entry_kind: "expense",
        entry_date: expenseForm.date || null,
        date_label: dateLabel,
        group_label: null,
        title: expenseForm.title.trim(),
        amount_value: parseAmount(expenseForm.amount),
        amount_expr: null,
        aux_amount_value: null,
        aux_amount_expr: null,
        extra_value: null,
        sort_order: nextSortOrder(entries),
      });
      setExpenseForm({ date: expenseForm.date, title: "", amount: "" });
      setStatus("당월 기록 추가 완료");
    });
  }

  async function handlePlannedSubmit(event: FormEvent) {
    event.preventDefault();
    if (!plannedForm.title.trim()) return;
    await withRefresh(async () => {
      await appendPlannedEntry({
        title: plannedForm.title.trim(),
        amount_value: parseAmount(plannedForm.amount),
      });
      setPlannedForm({ title: "", amount: "" });
      setStatus("나갈 돈 추가 완료");
    });
  }

  async function handlePanelSubmit(event: FormEvent) {
    event.preventDefault();
    if (!panelForm.title.trim()) return;
    await withRefresh(async () => {
      const sameTypePanels = panels.filter((panel) => panel.panel_type === panelForm.panel_type);
      await createPanel({
        month: currentMonth,
        panel_type: panelForm.panel_type,
        title: panelForm.title.trim(),
        amount_value: parseAmount(panelForm.amount),
        amount_expr: null,
        sort_order: nextSortOrder(sameTypePanels),
      });
      setPanelForm({ ...panelForm, title: "", amount: "" });
      setStatus(`${panelLabel(labels, panelForm.panel_type)} 항목 추가 완료`);
    });
  }

  async function handleCloseMonth() {
    const confirmed = window.confirm("나갈 돈을 제외한 당월 기록을 전체 기록으로 넘길까요?");
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
          <button type="button" onClick={() => void handleExport()} disabled={isBusy}>
            엑셀 export
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

      <section className="layout">
        <div className="left-column">
          <section className="panel">
            <div className="panel-header">
              <h2>나갈 돈</h2>
              <span>{formatWon(sumAmounts(plannedEntries))}</span>
            </div>
            <EntryTable entries={plannedEntries} emptyText="예정 지출이 없습니다." />
            <form className="inline-form" onSubmit={(event) => void handlePlannedSubmit(event)}>
              <input
                value={plannedForm.title}
                onChange={(event) => setPlannedForm({ ...plannedForm, title: event.target.value })}
                placeholder="적요"
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

          <section className="panel">
            <div className="panel-header">
              <h2>당월 기록</h2>
              <span>{formatWon(sumAmounts(expenseEntries))}</span>
            </div>
            <EntryTable entries={expenseEntries} emptyText="당월 지출이 없습니다." />
            <form className="entry-form" onSubmit={(event) => void handleExpenseSubmit(event)}>
              <input
                type="date"
                value={expenseForm.date}
                onChange={(event) => setExpenseForm({ ...expenseForm, date: event.target.value })}
              />
              <input
                value={expenseForm.title}
                onChange={(event) => setExpenseForm({ ...expenseForm, title: event.target.value })}
                placeholder="적요"
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
        </div>

        <aside className="right-column">
          <SummaryPanel summary={summary} labels={labels} />
          <section className="panel">
            <div className="panel-header">
              <h2>패널 추가</h2>
            </div>
            <form className="panel-form" onSubmit={(event) => void handlePanelSubmit(event)}>
              <select
                value={panelForm.panel_type}
                onChange={(event) =>
                  setPanelForm({ ...panelForm, panel_type: event.target.value as PanelType })
                }
              >
                {Object.keys(panelMeta).map((type) => (
                  <option value={type} key={type}>
                    {panelLabel(labels, type as PanelType)}
                  </option>
                ))}
              </select>
              <input
                value={panelForm.title}
                onChange={(event) => setPanelForm({ ...panelForm, title: event.target.value })}
                placeholder="적요"
              />
              <input
                value={panelForm.amount}
                onChange={(event) => setPanelForm({ ...panelForm, amount: event.target.value })}
                inputMode="numeric"
                placeholder="금액"
              />
              <button type="submit" disabled={isBusy}>
                추가
              </button>
            </form>
          </section>
          {(["fixed", "frozen", "claim", "settlement"] as PanelType[]).map((type) => (
            <PanelTable
              key={type}
              title={panelLabel(labels, type)}
              rows={panels.filter((panel) => panel.panel_type === type)}
            />
          ))}
        </aside>
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
        <h2>{labels.summary_title ?? "요약"}</h2>
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

function EntryTable({ entries, emptyText }: { entries: LedgerEntry[]; emptyText: string }) {
  if (!entries.length) return <p className="empty">{emptyText}</p>;
  return (
    <table>
      <thead>
        <tr>
          <th>날짜</th>
          <th>적요</th>
          <th className="amount">금액</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((entry) => (
          <tr key={entry.id}>
            <td className="date">{entry.date_label ?? entry.group_label ?? ""}</td>
            <td>{entry.title}</td>
            <td className="amount">{formatWon(entry.amount_value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PanelTable({ title, rows }: { title: string; rows: MonthlyPanel[] }) {
  return (
    <section className="panel compact">
      <div className="panel-header">
        <h2>{title}</h2>
        <span>{formatWon(sumPanelAmounts(rows))}</span>
      </div>
      {rows.length ? (
        <table>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id}>
                <td>{row.title}</td>
                <td className="amount">{formatWon(row.amount_value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty">항목이 없습니다.</p>
      )}
    </section>
  );
}

function panelLabel(labels: Record<string, string>, type: PanelType): string {
  const meta = panelMeta[type];
  return labels[meta.labelKey] ?? meta.fallback;
}

function parseAmount(value: string): number | null {
  const normalized = value.replaceAll(",", "").trim();
  if (!normalized) return null;
  const amount = Number(normalized);
  return Number.isFinite(amount) ? amount : null;
}

function nextSortOrder(rows: { sort_order: number }[]): number {
  return rows.reduce((max, row) => Math.max(max, row.sort_order), 0) + 1;
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

function sumAmounts(entries: LedgerEntry[]): number {
  return entries.reduce((total, entry) => total + (entry.amount_value ?? 0), 0);
}

function sumPanelAmounts(rows: MonthlyPanel[]): number {
  return rows.reduce((total, row) => total + (row.amount_value ?? 0), 0);
}

function formatWon(value: number | null): string {
  return `${Math.round(value ?? 0).toLocaleString("ko-KR")}원`;
}
