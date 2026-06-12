import { Dispatch, SetStateAction } from "react";

import {
  AuthUser,
  changePassword,
  clearAuditLogs,
  closeCurrentMonth,
  downloadPreRestoreBackup,
  fetchAuditLogs,
  fetchPreRestoreBackups,
  MonthCloseStatus,
  PreRestoreBackup,
  resetLedgerData,
  restorePreRestoreBackup,
  restoreSnapshot,
  setSharePin,
  updateSetting,
} from "../api";
import { formatMonthLabel, parseAmount } from "../utils";

export function useSettingsHandlers({
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
  setPasswordForm,
  setPaymentAllocations,
  setPreRestoreBackups,
  setResetPassword,
  setScheduledIncomeInput,
  setShowAuditLogs,
  setStatus,
  showAuditLogs,
  withRefresh,
}: {
  cardLimitInput: string;
  interestExpenseInput: string;
  monthCloseStatus: MonthCloseStatus | null;
  passwordForm: { currentPassword: string; newPassword: string };
  resetPassword: string;
  scheduledIncomeInput: string;
  setAuditLogs: (logs: Awaited<ReturnType<typeof fetchAuditLogs>>) => void;
  setAuthUser: Dispatch<SetStateAction<AuthUser | null>>;
  setCardLimitInput: (value: string) => void;
  setInterestExpenseInput: (value: string) => void;
  setIsBusy: (busy: boolean) => void;
  setPasswordForm: (value: { currentPassword: string; newPassword: string }) => void;
  setPaymentAllocations: (value: Record<string, string>) => void;
  setPreRestoreBackups: (value: PreRestoreBackup[]) => void;
  setResetPassword: (value: string) => void;
  setScheduledIncomeInput: (value: string) => void;
  setShowAuditLogs: (value: boolean) => void;
  setStatus: (value: string) => void;
  showAuditLogs: boolean;
  withRefresh: (action: () => Promise<void>) => Promise<void>;
}) {
  async function handleScheduledIncomeSave() {
    const amount = parseAmount(scheduledIncomeInput);
    if (amount === null || amount < 0) return;
    await withRefresh(async () => {
      await updateSetting("base_next_month_liquidity", String(amount));
      setScheduledIncomeInput(String(amount));
      setStatus("기본 예정 수입 저장 완료");
    });
  }

  async function handleInterestExpenseSave() {
    const amount = parseAmount(interestExpenseInput);
    if (amount === null || amount < 0) {
      setStatus("이자지출은 0원 이상의 숫자로 입력하세요.");
      return;
    }
    await withRefresh(async () => {
      await updateSetting("interest_expense", String(amount));
      setInterestExpenseInput(String(amount));
      setStatus("이자지출 저장 완료");
    });
  }

  async function handleCardLimitSave() {
    const amount = parseAmount(cardLimitInput);
    if (amount === null || amount < 0) {
      setStatus("카드 한도는 0원 이상의 숫자로 입력하세요.");
      return;
    }
    await withRefresh(async () => {
      await updateSetting("card_limit", String(amount));
      setCardLimitInput(String(amount));
      setStatus("카드 한도 저장 완료");
    });
  }

  async function handleCardLast4Save(key: "owner_card_last4" | "family_card_last4", value: string) {
    const trimmed = value.trim();
    if (trimmed && !/^\d{4}$/.test(trimmed)) {
      setStatus("카드 식별값은 비워두거나 숫자 네 자리로 입력해 주세요.");
      return;
    }
    await withRefresh(async () => {
      await updateSetting(key, trimmed);
      setStatus(key === "owner_card_last4" ? "본인 카드 식별값 저장 완료" : "가족카드 식별값 저장 완료");
    });
  }

  async function handlePasswordChange() {
    if (!passwordForm.currentPassword || !passwordForm.newPassword) {
      setStatus("현재 비밀번호와 새 비밀번호를 입력하세요.");
      return;
    }
    await withRefresh(async () => {
      await changePassword({
        current_password: passwordForm.currentPassword,
        new_password: passwordForm.newPassword,
      });
      setPasswordForm({ currentPassword: "", newPassword: "" });
      setStatus("계정 비밀번호 변경 완료");
    });
  }

  async function handleLedgerReset() {
    if (!resetPassword) {
      setStatus("장부 초기화에는 현재 비밀번호가 필요합니다.");
      return;
    }
    const confirmed = window.confirm(
      "장부 데이터를 전부 초기화할까요?\n\n당월/전체 기록, 청구, 가족카드, 현금흐름, 할부, 결제 기록이 삭제됩니다. 계정과 설정은 유지됩니다.",
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await resetLedgerData(resetPassword);
      const total = Object.values(result.deleted).reduce((sum, count) => sum + count, 0);
      setResetPassword("");
      setPaymentAllocations({});
      setStatus(`장부 데이터 ${total}개 초기화 완료`);
    });
  }

  async function handleSnapshotRestore(file: File | null) {
    if (!file) {
      setStatus("복원할 snapshot 파일을 선택하세요.");
      return;
    }
    if (!resetPassword) {
      setStatus("snapshot 복원에는 현재 비밀번호가 필요합니다.");
      return;
    }
    const confirmed = window.confirm(
      "snapshot을 복원할까요?\n\n기존 장부 운용 데이터가 snapshot 내용으로 교체됩니다. 계정, 로그인 세션, 공유 세션, 관리 로그는 유지됩니다.",
    );
    if (!confirmed) return;
    let snapshot: unknown;
    try {
      snapshot = JSON.parse(await file.text());
    } catch {
      setStatus("snapshot 파일을 JSON으로 읽지 못했습니다.");
      return;
    }
    await withRefresh(async () => {
      const result = await restoreSnapshot(resetPassword, snapshot);
      const total = Object.values(result.restored).reduce((sum, count) => sum + count, 0);
      setResetPassword("");
      setPaymentAllocations({});
      setStatus(`snapshot 복원 완료: ${total}행`);
    });
  }

  async function handlePreRestoreList() {
    setIsBusy(true);
    try {
      const backups = await fetchPreRestoreBackups();
      setPreRestoreBackups(backups);
      setStatus(`복원 전 백업 ${backups.length}개 조회 완료`);
    } catch (error) {
      setStatus(`복원 전 백업 조회 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePreRestoreDownload(filename: string) {
    setIsBusy(true);
    try {
      const result = await downloadPreRestoreBackup(filename);
      const url = URL.createObjectURL(result.blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setStatus("복원 전 백업 다운로드 준비 완료");
    } catch (error) {
      setStatus(`복원 전 백업 다운로드 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handlePreRestoreRestore(filename: string) {
    if (!resetPassword) {
      setStatus("복원 전 백업으로 되돌리려면 현재 비밀번호가 필요합니다.");
      return;
    }
    const confirmed = window.confirm(
      `${filename}\n\n이 복원 전 백업 상태로 되돌릴까요?\n현재 장부 운용 데이터가 교체되며, 되돌리기 직전 상태도 새 pre_restore로 저장됩니다.`,
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await restorePreRestoreBackup(filename, resetPassword);
      const total = Object.values(result.restored).reduce((sum, count) => sum + count, 0);
      setResetPassword("");
      setPaymentAllocations({});
      setPreRestoreBackups(await fetchPreRestoreBackups());
      setStatus(`복원 전 백업으로 되돌리기 완료: ${total}행`);
    });
  }

  async function handleSharePinSet() {
    const pin = window.prompt("가족 공유 페이지에서 사용할 숫자 네 자리를 입력하세요.");
    if (pin === null) return;
    if (!/^[0-9]{4}$/.test(pin)) {
      setStatus("공유 PIN은 숫자 네 자리여야 합니다.");
      return;
    }
    await withRefresh(async () => {
      const result = await setSharePin(pin);
      setAuthUser((user) => (user ? { ...user, share_pin_needs_change: result.needs_change } : user));
      setStatus(
        result.needs_change
          ? "0000은 기본 PIN입니다. 공유 페이지 보호를 위해 다른 PIN으로 변경하세요."
          : "가족 공유 PIN 설정 완료. 기존 공유 세션은 종료되었습니다.",
      );
    });
  }

  async function handleAuditLogToggle() {
    if (showAuditLogs) {
      setShowAuditLogs(false);
      return;
    }
    setIsBusy(true);
    try {
      setAuditLogs(await fetchAuditLogs());
      setShowAuditLogs(true);
      setStatus("관리 로그 조회 완료");
    } catch (error) {
      setStatus(`관리 로그 조회 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleAuditLogClear() {
    const confirmed = window.confirm("관리 로그를 전부 초기화할까요?\n\n이 작업은 되돌릴 수 없습니다.");
    if (!confirmed) return;
    setIsBusy(true);
    try {
      const result = await clearAuditLogs();
      setAuditLogs([]);
      setStatus(`관리 로그 ${result.deleted}개 초기화 완료`);
    } catch (error) {
      setStatus(`관리 로그 초기화 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  async function handleCloseMonth() {
    const targetMonth = monthCloseStatus?.oldest_open_month;
    const isEarlyClose = Boolean(targetMonth && targetMonth === monthCloseStatus?.calendar_month);
    const confirmed = window.confirm(
      isEarlyClose
        ? `${formatMonthLabel(targetMonth!)}을 조기 월마감할까요?\n\n이후 같은 달 날짜로 추가하는 지출은 전체 기록에 바로 보관됩니다. 청구와 가족카드는 영향을 받지 않습니다.`
        : targetMonth
        ? `${formatMonthLabel(targetMonth)} 기록만 월마감하여 전체 기록으로 넘길까요?`
        : "가장 오래된 미마감 월 기록을 전체 기록으로 넘길까요?",
    );
    if (!confirmed) return;
    await withRefresh(async () => {
      const result = await closeCurrentMonth(isEarlyClose);
      setStatus(
        result.closed_month
          ? `${formatMonthLabel(result.closed_month)} 월마감 완료: ${result.archived}개 archive`
          : "월마감할 기록이 없습니다.",
      );
    });
  }

  return {
    handleAuditLogClear,
    handleAuditLogToggle,
    handleCardLast4Save,
    handleCloseMonth,
    handleCardLimitSave,
    handleInterestExpenseSave,
    handleLedgerReset,
    handlePasswordChange,
    handlePreRestoreDownload,
    handlePreRestoreList,
    handlePreRestoreRestore,
    handleScheduledIncomeSave,
    handleSharePinSet,
    handleSnapshotRestore,
  };
}
