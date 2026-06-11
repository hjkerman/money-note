import { MonthCloseStatus } from "../api";

export function AppHeader({
  currentMonth,
  isBusy,
  monthCloseStatus,
  onAuditLogToggle,
  onCloseMonth,
  onLogout,
  onOpenSettings,
  onShowStatsToggle,
  showStats,
}: {
  currentMonth: string;
  isBusy: boolean;
  monthCloseStatus: MonthCloseStatus | null;
  onAuditLogToggle: () => void;
  onCloseMonth: () => void;
  onLogout: () => void;
  onOpenSettings: () => void;
  onShowStatsToggle: () => void;
  showStats: boolean;
}) {
  return (
    <header className="topbar">
      <div>
        <h1>money-note</h1>
        <p>{currentMonth} 당월 기록</p>
      </div>
      <div className="actions">
        <button type="button" onClick={onOpenSettings} disabled={isBusy}>
          설정
        </button>
        <button type="button" onClick={onShowStatsToggle} disabled={isBusy}>
          통계 {showStats ? "끄기" : "보기"}
        </button>
        <button type="button" onClick={onAuditLogToggle} disabled={isBusy}>
          관리 로그
        </button>
        <button
          type="button"
          className="danger"
          onClick={onCloseMonth}
          disabled={isBusy || !monthCloseStatus?.can_close}
        >
          월마감
        </button>
        <button type="button" onClick={onLogout} disabled={isBusy}>
          로그아웃
        </button>
      </div>
    </header>
  );
}
