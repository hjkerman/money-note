import { Dispatch, FormEvent, SetStateAction } from "react";

type LoginForm = { username: string; password: string };

export function InitialLoadingView() {
  return (
    <main className="login-shell">
      <section className="login-card">
        <h1>money-note</h1>
        <p>서버와 통신 준비 중</p>
      </section>
    </main>
  );
}

export function LoginView({
  isBusy,
  loginForm,
  onLogin,
  setLoginForm,
  status,
}: {
  isBusy: boolean;
  loginForm: LoginForm;
  onLogin: (event: FormEvent) => void;
  setLoginForm: Dispatch<SetStateAction<LoginForm>>;
  status: string;
}) {
  return (
    <main className="login-shell">
      <section className="login-card">
        <h1>money-note</h1>
        <p>가계부를 조작하려면 로그인이 필요합니다.</p>
        <form onSubmit={onLogin}>
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
