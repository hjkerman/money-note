import {
  AuditLog,
  CardDiscountMonth,
  CardDiscountPolicy,
  JudgmentState,
  SpendingCategory,
  Summary,
} from "../api";
import { StatItem } from "../types";
import {
  fallbackCategoryLabels,
  formatAuditTimestamp,
  formatMonthLabel,
  formatWon,
  sumStatItems,
} from "../utils";

export function SummaryPanel({
  summary,
  judgment,
  labels,
}: {
  summary: Summary | null;
  judgment: JudgmentState | null;
  labels: Record<string, string>;
}) {
  const committee = judgment?.budget ?? {
    level: "quiet",
    message: "판단 모듈이 서버 응답을 기다리고 있습니다.",
  };
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

export function AuditLogPanel({ logs, onClear, isBusy }: { logs: AuditLog[]; onClear: () => void; isBusy: boolean }) {
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

export function StatsPanel({ items, judgment }: { items: StatItem[]; judgment: JudgmentState | null }) {
  const tones = judgment?.stat_tones ?? [
    { key: "essential" as SpendingCategory, title: fallbackCategoryLabels.essential, caption: "생존 인프라입니다." },
    { key: "questionable" as SpendingCategory, title: fallbackCategoryLabels.questionable, caption: "예산위원회 출석 안건입니다." },
    { key: "dignity" as SpendingCategory, title: fallbackCategoryLabels.dignity, caption: "사람 꼴 유지 비용입니다." },
    { key: null, title: fallbackCategoryLabels.unclassified, caption: "아직 판결 전입니다." },
  ];
  const rows = tones.map((tone) => ({
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

export function CreditUsagePanel({
  cardLimit,
  currentCardTotal,
  settlementTotal,
  tone,
}: {
  cardLimit: number;
  currentCardTotal: number;
  settlementTotal: number;
  tone: JudgmentState["credit"] | null;
}) {
  const combinedTotal = currentCardTotal + settlementTotal;
  const usageRate = cardLimit > 0 ? combinedTotal / cardLimit : 0;
  const usagePercent = usageRate * 100;
  const width = Math.min(100, Math.max(0, usagePercent));
  const creditTone = tone ?? { level: "quiet", message: "가족카드 판단을 불러오는 중입니다." };
  return (
    <section className={`panel credit-panel ${creditTone.level}`}>
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
      <p>{creditTone.message}</p>
      <p className="credit-note">할부와 일시불이 섞이면 실제 한도 차감액은 카드사 기준과 다를 수 있습니다.</p>
    </section>
  );
}

export function DiscountPolicyBar({
  month,
  scope,
  status,
  onChange,
  isBusy,
}: {
  month: string;
  scope: "owner" | "family";
  status: CardDiscountMonth | null;
  onChange: (scope: "owner" | "family", month: string, policy: CardDiscountPolicy) => void;
  isBusy: boolean;
}) {
  const label = scope === "family" ? "가족카드" : "본인회원 카드";
  return (
    <section className={`discount-policy ${status?.policy ?? "undecided"}`}>
      <div>
        <strong>{formatMonthLabel(month)} {label} 할인 혜택</strong>
        <span>
          {status?.policy === "enabled"
            ? "혜택 있음 · 항목별 할인액을 기록할 수 있습니다."
            : status?.policy === "disabled"
              ? "혜택 없음 · 할인액 입력을 막습니다."
              : "아직 정하지 않았습니다. 확인 후 선택하세요."}
        </span>
      </div>
      <select
        value={status?.policy ?? "undecided"}
        onChange={(event) => onChange(scope, month, event.target.value as CardDiscountPolicy)}
        disabled={isBusy}
        aria-label={`${label} 할인 혜택 설정`}
      >
        <option value="undecided">미정</option>
        <option value="enabled">혜택 있음</option>
        <option value="disabled">혜택 없음</option>
      </select>
    </section>
  );
}
