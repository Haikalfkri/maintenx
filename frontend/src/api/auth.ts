import type { CurrentUser, Tokens } from "../types";
import { api } from "./client";

export async function requestTokens(email: string, password: string): Promise<Tokens> {
    const { data } = await api.post<Tokens>("/auth/token/", { email, password });
    return data;
}

export async function fetchMe(): Promise<CurrentUser> {
  const { data } = await api.get<CurrentUser>("/auth/me/");
  return data;
}

export async function requestLogout(refresh: string): Promise<void> {
  await api.post("/auth/logout/", { refresh });
}