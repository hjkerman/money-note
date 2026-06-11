import { Dispatch, SetStateAction } from "react";

type PasswordForm = { currentPassword: string; newPassword: string };

export function SettingsModal({
  familyCardLast4Input,
  familyCardLimitInput,
  interestExpenseInput,
  isBusy,
  onCardLast4Save,
  onClose,
  onFamilyCardLimitSave,
  onInterestExpenseSave,
  onLedgerReset,
  onPasswordChange,
  onScheduledIncomeSave,
  onSharePinSet,
  ownerCardLast4Input,
  passwordForm,
  resetPassword,
  scheduledIncomeInput,
  setFamilyCardLast4Input,
  setFamilyCardLimitInput,
  setInterestExpenseInput,
  setOwnerCardLast4Input,
  setPasswordForm,
  setResetPassword,
  setScheduledIncomeInput,
}: {
  familyCardLast4Input: string;
  familyCardLimitInput: string;
  interestExpenseInput: string;
  isBusy: boolean;
  onCardLast4Save: (key: "owner_card_last4" | "family_card_last4", value: string) => void;
  onClose: () => void;
  onFamilyCardLimitSave: () => void;
  onInterestExpenseSave: () => void;
  onLedgerReset: () => void;
  onPasswordChange: () => void;
  onScheduledIncomeSave: () => void;
  onSharePinSet: () => void;
  ownerCardLast4Input: string;
  passwordForm: PasswordForm;
  resetPassword: string;
  scheduledIncomeInput: string;
  setFamilyCardLast4Input: Dispatch<SetStateAction<string>>;
  setFamilyCardLimitInput: Dispatch<SetStateAction<string>>;
  setInterestExpenseInput: Dispatch<SetStateAction<string>>;
  setOwnerCardLast4Input: Dispatch<SetStateAction<string>>;
  setPasswordForm: Dispatch<SetStateAction<PasswordForm>>;
  setResetPassword: Dispatch<SetStateAction<string>>;
  setScheduledIncomeInput: Dispatch<SetStateAction<string>>;
}) {
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
            <span>예정 수입</span>
            <input
              type="number"
              min="0"
              step="1"
              value={scheduledIncomeInput}
              onChange={(event) => setScheduledIncomeInput(event.target.value)}
              inputMode="numeric"
              placeholder="예정 수입"
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
            <span>가족카드 한도</span>
            <input
              type="number"
              min="0"
              step="1"
              value={familyCardLimitInput}
              onChange={(event) => setFamilyCardLimitInput(event.target.value)}
              inputMode="numeric"
              placeholder="가족카드 한도"
            />
            <button type="button" onClick={onFamilyCardLimitSave} disabled={isBusy}>
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
            <div>
              <h3>장부 데이터 전체 초기화</h3>
              <p>계정, 로그인 세션, 공유 PIN, 설정은 유지하고 사용자가 입력한 장부 운용 데이터만 삭제합니다.</p>
            </div>
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
          </section>
        </div>
      </section>
    </div>
  );
}
