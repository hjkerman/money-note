import { Dispatch, FormEvent, SetStateAction, useState } from "react";
import { AuthUser, fetchMe, login, logout } from "../api";
import { isAuthRequiredError } from "../utils";

type LoginForm = { username: string; password: string };

export function useAuthSession({
  loginForm,
  onLogoutClear,
  onRefresh,
  setIsBusy,
  setLoginForm,
  setStatus,
}: {
  loginForm: LoginForm;
  onLogoutClear: () => void;
  onRefresh: () => Promise<void>;
  setIsBusy: Dispatch<SetStateAction<boolean>>;
  setLoginForm: Dispatch<SetStateAction<LoginForm>>;
  setStatus: Dispatch<SetStateAction<string>>;
}) {
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authChecked, setAuthChecked] = useState(false);

  function handleAuthRequired() {
    setAuthUser(null);
    setStatus("로그인이 필요합니다.");
  }

  async function checkAuth() {
    setIsBusy(true);
    try {
      const user = await fetchMe();
      setAuthUser(user);
      await onRefresh();
    } catch (error) {
      if (!isAuthRequiredError(error)) {
        setStatus(`서버 통신 실패: ${error instanceof Error ? error.message : String(error)}`);
      } else {
        handleAuthRequired();
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
      setStatus(
        user.share_pin_needs_change
          ? "로그인 완료. 가족 공유 PIN이 기본값 0000입니다. 지금 변경하세요."
          : "로그인 완료",
      );
      await onRefresh();
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
      onLogoutClear();
      setStatus("로그아웃 완료");
    } catch (error) {
      setStatus(`로그아웃 실패: ${error instanceof Error ? error.message : String(error)}`);
    } finally {
      setIsBusy(false);
    }
  }

  return {
    authChecked,
    authUser,
    checkAuth,
    handleAuthRequired,
    handleLogin,
    handleLogout,
    setAuthUser,
  };
}
