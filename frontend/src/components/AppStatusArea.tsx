import { AuthUser, AuditLog, MonthCloseStatus } from "../api";
import { formatMonthLabel } from "../utils";
import { AuditLogPanel } from "./Insights";

export function AppStatusArea({
  auditLogs,
  authUser,
  isBusy,
  monthCloseStatus,
  onAuditLogClear,
  onCloseMonth,
  onSharePinSet,
  showAuditLogs,
  status,
}: {
  auditLogs: AuditLog[];
  authUser: AuthUser;
  isBusy: boolean;
  monthCloseStatus: MonthCloseStatus | null;
  onAuditLogClear: () => void;
  onCloseMonth: () => void;
  onSharePinSet: () => void;
  showAuditLogs: boolean;
  status: string;
}) {
  return (
    <>
      <section className="statusline">{status}</section>
      {showAuditLogs ? (
        <AuditLogPanel logs={auditLogs} onClear={onAuditLogClear} isBusy={isBusy} />
      ) : null}
      {authUser.share_pin_needs_change ? (
        <section className="security-warning">
          <div>
            <strong>가족 공유 PIN이 아직 기본값 0000입니다.</strong>
            <span>공유 링크를 보내기 전에 가족 공식 비밀번호로 변경하세요.</span>
          </div>
          <button type="button" className="save-needed" onClick={onSharePinSet} disabled={isBusy}>
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
          <button type="button" className="save-needed" onClick={onCloseMonth} disabled={isBusy}>
            월마감 검토
          </button>
        </section>
      ) : null}
    </>
  );
}
