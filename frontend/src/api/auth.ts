import { getJson, patchJson, postJson } from "./client";
import { AuthUser } from "./types";

export async function fetchMe(): Promise<AuthUser> {
  return getJson("/api/auth/me");
}

export async function login(payload: { username: string; password: string }): Promise<AuthUser> {
  return postJson<AuthUser>("/api/auth/login", payload);
}

export async function logout(): Promise<{ ok: boolean }> {
  return postJson("/api/auth/logout", {});
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
}): Promise<{ changed: boolean }> {
  return patchJson("/api/auth/password", payload);
}
