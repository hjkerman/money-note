import { Dispatch, SetStateAction, useRef, useState } from "react";

import { OperationStats, PreRestoreBackup } from "../api";

type PasswordForm = { currentPassword: string; newPassword: string };

export function SettingsModal({
  familyCardLast4Input,
  cardLimitInput,
  interestExpenseInput,
  isBusy,
  onCardLast4Save,
  onApkDownload,
  onClose,
  onCardLimitSave,
  onInterestExpenseSave,
  onLedgerReset,
  onOperationStatsLoad,
  onPasswordChange,
  onPreRestoreDelete,
  onPreRestoreDeleteAll,
  onPreRestoreList,
  onPreRestoreRestore,
  onScheduledIncomeSave,
  onSharePinSet,
  onSnapshotDownload,
  onSnapshotRestore,
  ownerCardLast4Input,
  operationStats,
  passwordForm,
  preRestoreBackups,
  resetPassword,
  scheduledIncomeInput,
  setFamilyCardLast4Input,
  setCardLimitInput,
  setInterestExpenseInput,
  setOwnerCardLast4Input,
  setPasswordForm,
  setResetPassword,
  setScheduledIncomeInput,
}: {
  familyCardLast4Input: string;
  cardLimitInput: string;
  interestExpenseInput: string;
  isBusy: boolean;
  onCardLast4Save: (key: "owner_card_last4" | "family_card_last4", value: string) => void;
  onApkDownload: () => void;
  onClose: () => void;
  onCardLimitSave: () => void;
  onInterestExpenseSave: () => void;
  onLedgerReset: () => void;
  onOperationStatsLoad: () => void;
  onPasswordChange: () => void;
  onPreRestoreDelete: (filename: string) => void;
  onPreRestoreDeleteAll: () => void;
  onPreRestoreList: () => void;
  onPreRestoreRestore: (filename: string) => void;
  onScheduledIncomeSave: () => void;
  onSharePinSet: () => void;
  onSnapshotDownload: () => void;
  onSnapshotRestore: (file: File | null) => void;
  ownerCardLast4Input: string;
  operationStats: OperationStats | null;
  passwordForm: PasswordForm;
  preRestoreBackups: PreRestoreBackup[];
  resetPassword: string;
  scheduledIncomeInput: string;
  setFamilyCardLast4Input: Dispatch<SetStateAction<string>>;
  setCardLimitInput: Dispatch<SetStateAction<string>>;
  setInterestExpenseInput: Dispatch<SetStateAction<string>>;
  setOwnerCardLast4Input: Dispatch<SetStateAction<string>>;
  setPasswordForm: Dispatch<SetStateAction<PasswordForm>>;
  setResetPassword: Dispatch<SetStateAction<string>>;
  setScheduledIncomeInput: Dispatch<SetStateAction<string>>;
}) {
  const snapshotInputRef = useRef<HTMLInputElement | null>(null);
  const [snapshotFile, setSnapshotFile] = useState<File | null>(null);

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="settings-modal"
        role="dialog"
        aria-modal="true"
        aria-label="설정"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="panel-header">
          <h2>설정</h2>
          <button type="button" onClick={onClose}>
            닫기
          </button>
        </div>
        <div className="settings-grid">
          <label>
            <span>기본 예정 수입</span>
            <input
              type="number"
              min="0"
              step="1"
              value={scheduledIncomeInput}
              onChange={(event) => setScheduledIncomeInput(event.target.value)}
              inputMode="numeric"
              placeholder="기본 예정 수입"
            />
            <button type="button" onClick={onScheduledIncomeSave} disabled={isBusy}>
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
            <button type="button" onClick={onInterestExpenseSave} disabled={isBusy}>
              저장
            </button>
          </label>
          <label>
            <span>카드 한도</span>
            <input
              type="number"
              min="0"
              step="1"
              value={cardLimitInput}
              onChange={(event) => setCardLimitInput(event.target.value)}
              inputMode="numeric"
              placeholder="카드 한도"
            />
            <button type="button" onClick={onCardLimitSave} disabled={isBusy}>
              저장
            </button>
          </label>
          <label>
            <span>본인 카드 끝 4자리</span>
            <input
              value={ownerCardLast4Input}
              onChange={(event) => setOwnerCardLast4Input(event.target.value)}
              inputMode="numeric"
              maxLength={4}
              placeholder="선택 입력"
            />
            <button
              type="button"
              onClick={() => onCardLast4Save("owner_card_last4", ownerCardLast4Input)}
              disabled={isBusy}
            >
              저장
            </button>
          </label>
          <label>
            <span>가족카드 끝 4자리</span>
            <input
              value={familyCardLast4Input}
              onChange={(event) => setFamilyCardLast4Input(event.target.value)}
              inputMode="numeric"
              maxLength={4}
              placeholder="선택 입력"
            />
            <button
              type="button"
              onClick={() => onCardLast4Save("family_card_last4", familyCardLast4Input)}
              disabled={isBusy}
            >
              저장
            </button>
          </label>
          <div className="settings-row">
            <span>가족 공유 PIN</span>
            <button type="button" onClick={onSharePinSet} disabled={isBusy}>
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
              minLength={12}
              placeholder="새 비밀번호(12자 이상)"
            />
            <button type="button" onClick={onPasswordChange} disabled={isBusy}>
              변경
            </button>
          </label>
          <section className="settings-row settings-download-row">
            <div>
              <span>Android 앱 설치 파일</span>
              <p>서버에 올려둔 최신 APK 파일을 내려받습니다.</p>
            </div>
            <button type="button" onClick={onApkDownload} disabled={isBusy}>
              APK 다운로드
            </button>
          </section>
          <section className="danger-zone">
            <article className="danger-action">
              <div>
                <h3>snapshot 백업</h3>
                <p>현재 장부와 설정을 단일 snapshot 파일로 내려받습니다. 비밀번호 재확인은 필요 없습니다.</p>
              </div>
              <button type="button" onClick={onSnapshotDownload} disabled={isBusy}>
                snapshot 백업 다운로드
              </button>
            </article>
            <article className="danger-action">
              <div>
                <h3>snapshot 복원</h3>
                <p>장부 운용 데이터를 snapshot 파일 내용으로 교체합니다. 현재 비밀번호 확인이 필요합니다.</p>
              </div>
              <div className="danger-controls">
                <input
                  ref={snapshotInputRef}
                  type="file"
                  accept=".money-note-snapshot.json,application/json"
                  onChange={(event) => setSnapshotFile(event.target.files?.[0] ?? null)}
                />
                <button
                  type="button"
                  className="danger"
                  onClick={() => {
                    onSnapshotRestore(snapshotFile);
                    if (snapshotInputRef.current) snapshotInputRef.current.value = "";
                    setSnapshotFile(null);
                  }}
                  disabled={isBusy || !snapshotFile}
                >
                  snapshot 복원
                </button>
              </div>
            </article>
            <article className="danger-action">
              <div>
                <h3>장부 데이터 전체 초기화</h3>
                <p>계정, 로그인 세션, 공유 PIN, 설정은 유지하고 사용자가 입력한 장부 운용 데이터만 삭제합니다.</p>
              </div>
              <div className="danger-controls">
                <input
                  type="password"
                  value={resetPassword}
                  onChange={(event) => setResetPassword(event.target.value)}
                  autoComplete="current-password"
                  placeholder="현재 비밀번호"
                />
                <button type="button" className="danger" onClick={onLedgerReset} disabled={isBusy}>
                  전체 초기화
                </button>
              </div>
            </article>
            <div className="pre-restore-section">
              <div className="pre-restore-header">
                <div>
                  <h3>복원 전 백업</h3>
                  <p>복원, 월마감, 초기화, 일괄 처리 직전에 서버가 자동으로 남긴 안전장치입니다.</p>
                </div>
                <div className="pre-restore-actions">
                  <button type="button" onClick={onPreRestoreList} disabled={isBusy}>
                    목록 조회
                  </button>
                  <button
                    type="button"
                    className="danger"
                    onClick={onPreRestoreDeleteAll}
                    disabled={isBusy || preRestoreBackups.length === 0}
                  >
                    일괄 삭제
                  </button>
                </div>
              </div>
              {preRestoreBackups.length ? (
                <div className="pre-restore-list">
                  {preRestoreBackups.map((backup) => (
                    <article key={backup.filename} className="pre-restore-item">
                      <div>
                        <strong>{formatBackupDate(backup.created_at)}</strong>
                        <span>{formatBytes(backup.size_bytes)}</span>
                        <code>{backup.snapshot_id.slice(0, 16)}</code>
                      </div>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => onPreRestoreDelete(backup.filename)}
                        disabled={isBusy}
                      >
                        삭제
                      </button>
                      <button
                        type="button"
                        className="danger"
                        onClick={() => onPreRestoreRestore(backup.filename)}
                        disabled={isBusy}
                      >
                        되돌리기
                      </button>
                    </article>
                  ))}
                </div>
              ) : (
                <p className="pre-restore-empty">아직 조회된 복원 전 백업이 없습니다.</p>
              )}
            </div>
          </section>
          <section className="operation-stats-section">
            <div className="operation-stats-header">
              <div>
                <h3>운영 데이터 크기</h3>
                <p>DB 테이블 행 수와 백업 파일 크기를 확인합니다.</p>
              </div>
              <button type="button" onClick={onOperationStatsLoad} disabled={isBusy}>
                새로고침
              </button>
            </div>
            {operationStats ? (
              <>
                <div className="operation-stats-grid">
                  <div>
                    <span>SQLite 파일</span>
                    <strong>{formatBytes(operationStats.db_file_size_bytes)}</strong>
                  </div>
                  <div>
                    <span>추정 운영 데이터</span>
                    <strong>{formatBytes(operationStats.estimated_data_size_bytes)}</strong>
                  </div>
                  <div>
                    <span>빈 DB 기준</span>
                    <strong>{formatBytes(operationStats.empty_db_size_bytes)}</strong>
                  </div>
                  <div>
                    <span>pre_restore</span>
                    <strong>
                      {formatBytes(operationStats.pre_restore_total_size_bytes)} · {operationStats.pre_restore_count}개
                    </strong>
                  </div>
                </div>
                <div className="table-counts">
                  {Object.entries(operationStats.table_row_counts).map(([table, count]) => (
                    <div key={table}>
                      <code>{table}</code>
                      <span>{count.toLocaleString()}행</span>
                    </div>
                  ))}
                </div>
              </>
            ) : (
              <p className="pre-restore-empty">운영 데이터 통계를 아직 불러오지 않았습니다.</p>
            )}
          </section>
        </div>
      </section>
    </div>
  );
}

function formatBackupDate(value: string | null): string {
  if (!value) return "알 수 없음";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatBytes(value: number): string {
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}
