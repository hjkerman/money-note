const SESSION_TOKEN_KEY = "money-note-session-token";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? defaultApiBaseUrl();

export function storeSessionToken(token: string | null | undefined): void {
  if (token) localStorage.setItem(SESSION_TOKEN_KEY, token);
}

export function clearSessionToken(): void {
  localStorage.removeItem(SESSION_TOKEN_KEY);
}

export async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: authHeaders(),
    credentials: "include",
  });
  return parseResponse(response);
}

export async function postJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

export async function patchJson<T>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    credentials: "include",
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

export async function deleteJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "DELETE",
    headers: authHeaders(),
    credentials: "include",
  });
  return parseResponse(response);
}

export function authHeaders(): Record<string, string> {
  const token = localStorage.getItem(SESSION_TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function readDownloadFilename(header: string | null): string | null {
  if (!header) return null;
  const match = header.match(/filename="([^"]+)"/);
  return match?.[1] ?? null;
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.addEventListener("load", () => {
      const result = String(reader.result ?? "");
      resolve(result.includes(",") ? result.split(",")[1] : result);
    });
    reader.addEventListener("error", () => reject(reader.error ?? new Error("파일을 읽지 못했습니다.")));
    reader.readAsDataURL(file);
  });
}

function defaultApiBaseUrl(): string {
  if (typeof window === "undefined") return "http://127.0.0.1:18080";
  const { protocol, hostname } = window.location;
  if (hostname === "localhost" || hostname === "127.0.0.1") {
    return `${protocol}//${hostname}:18080`;
  }
  return "http://127.0.0.1:18080";
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(readableErrorMessage(response.status, detail));
  }
  return response.json() as Promise<T>;
}

export function readableErrorMessage(status: number, detail: string): string {
  const parsedDetail = parseErrorDetail(detail);
  if (status === 401 && parsedDetail === "invalid username or password") {
    return "아이디 또는 비밀번호가 맞지 않습니다.";
  }
  if (status === 401 && parsedDetail === "authentication required") {
    return "authentication required";
  }
  return parsedDetail || `HTTP ${status}`;
}

function parseErrorDetail(detail: string): string {
  if (!detail) return "";
  try {
    const parsed = JSON.parse(detail) as { detail?: unknown };
    if (typeof parsed.detail === "string") return parsed.detail;
  } catch {
    return detail;
  }
  return detail;
}
