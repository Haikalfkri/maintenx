import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios";

import type { Tokens } from "../types";

export const API_URL: string = 
    (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000/api/v1";

const ACCESS_KEY = "maintenx.access";
const REFRESH_KEY = "maintenx.refresh";

export const tokenStorage = {
    getAccess(): string | null {
        try {
            return localStorage.getItem(ACCESS_KEY);
        } catch {
            return null;
        }
    },
    getRefresh(): string | null {
        try {
            return localStorage.getItem(REFRESH_KEY);
        } catch {
            return null;
        }
    },
    set(tokens: Tokens): void {
        try {
            localStorage.setItem(ACCESS_KEY, tokens.access);
            localStorage.setItem(REFRESH_KEY, tokens.refresh);
        } catch {
            // pass
        }
    },
    clear(): void {
        try {
            localStorage.removeItem(ACCESS_KEY);
            localStorage.removeItem(REFRESH_KEY);
        } catch {
            // pass
        }
    }
};

let onSessionExpired: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null): void {
  onSessionExpired = handler;
}

export const api = axios.create({
    baseURL: API_URL,
    headers: { "Content-Type": "application/json" }
})

api.interceptors.request.use((config) => {
  const access = tokenStorage.getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

type RetriableRequest = InternalAxiosRequestConfig & { _retry?: boolean };

let refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refresh = tokenStorage.getRefresh();
  if (!refresh) throw new Error("No refresh token");
  const { data } = await axios.post<Tokens>(`${API_URL}/auth/token/refresh/`, { refresh });
  tokenStorage.set(data);
  return data.access;
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as RetriableRequest | undefined;
    const url = original?.url ?? "";
    const isAuthCall = url.startsWith("/auth/token") || url.startsWith("/auth/logout");

    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthCall &&
      tokenStorage.getRefresh()
    ) {
      original._retry = true;
      try {
        refreshPromise ??= refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
        const access = await refreshPromise;
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch {
        tokenStorage.clear();
        onSessionExpired?.();
      }
    }
    return Promise.reject(error);
  },
);