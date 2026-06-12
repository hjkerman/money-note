import { Dispatch, SetStateAction, useRef, useState } from "react";

import { PreRestoreBackup } from "../api";

type PasswordForm = { currentPassword: string; newPassword: string };

export function SettingsModal({
  familyCardLast4Input,
  cardLimitInput,
  interestExpenseInput,
  isBusy,
  onCardLast4Save,
  onClose,
  onCardLimitSave,
  onInterestExpenseSave,
  onLedgerReset,
  onPasswordChange,
  onPreRestoreDownload,
  onPreRestoreList,
  onPreRestoreRestore,
  onScheduledIncomeSave,
  onSharePinSet,
  onSnapshotDownload,
  onSnapshotRestore,
  ownerCardLast4Input,
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
  onClose: () => void;
  onCardLimitSave: () => void;
  onInterestExpenseSave: () => void;
  onLedgerReset: () => void;
  onPasswordChange: () => void;
  onPreRestoreDownload: (filename: string) => void;
  onPreRestoreList: () => void;
  onPreRestoreRestore: (filename: string) => void;
  onScheduledIncomeSave: () => void;
  onSharePinSet: () => void;
  onSnapshotDownload: () => void;
  onSnapshotRestore: (file: File | null) => void;
  ownerCardLast4Input: string;
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
              placeholder="새 비밀번호"
            />
            <button type="button" onClick={onPasswordChange} disabled={isBusy}>
              변경
            </button>
          </label>
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
                  <p>snapshot 복원 직전에 서버가 자동으로 남긴 안전장치입니다.</p>
                </div>
                <button type="button" onClick={onPreRestoreList} disabled={isBusy}>
                  목록 조회
                </button>
              </div>
              {preRestoreBackups.length ? (
                <div className="pre-restore-list">
                  {preRestoreBackups.map((backup) => (
                    <article key={backup.filename} className="pre-restore-item">
                      <div>
                        <strong>{backup.filename}</strong>
                        <span>
                          생성 {formatBackupDate(backup.created_at)} · export {formatBackupDate(backup.exported_at)} ·{" "}
                          {formatBytes(backup.size_bytes)}
                        </span>
                        <code>{backup.snapshot_id.slice(0, 16)}</code>
                      </div>
                      <button type="button" onClick={() => onPreRestoreDownload(backup.filename)} disabled={isBusy}>
                        다운로드
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
