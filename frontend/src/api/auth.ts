import { clearSessionToken, getJson, patchJson, postJson, storeSessionToken } from "./client";
import { AuthUser } from "./types";

export async function fetchMe(): Promise<AuthUser> {
  return getJson("/api/auth/me");
}

export async function login(payload: { username: string; password: string }): Promise<AuthUser> {
  const user = await postJson<AuthUser>("/api/auth/login", payload);
  storeSessionToken(user.session_token);
  return user;
}

export async function logout(): Promise<{ ok: boolean }> {
  try {
    return await postJson("/api/auth/logout", {});
  } finally {
    clearSessionToken();
  }
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<{ changed: boolean }> {
  return patchJson("/api/auth/password", payload);
}
