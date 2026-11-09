import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useState, type ReactNode } from "react";

import { fetchMe, requestLogout, requestTokens } from "../api/auth";
import { setSessionExpiredHandler, tokenStorage } from "../api/client";
import { AuthContext, type AuthContextValue } from "../hooks/auth-context";
import type { CurrentUser } from "../types";

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(() => tokenStorage.getRefresh() !== null);

  useEffect(() => {
    if (tokenStorage.getRefresh() === null) return;

    let cancelled = false;
    fetchMe()
      .then((me) => {
        if (!cancelled) setUser(me);
      })
      .catch(() => tokenStorage.clear())
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Saat refresh token gagal di tengah pemakaian: keluarkan user
  useEffect(() => {
    setSessionExpiredHandler(() => {
      queryClient.clear();
      setUser(null);
    });
    return () => setSessionExpiredHandler(null);
  }, [queryClient]);

  const login = useCallback(
    async (email: string, password: string) => {
      const tokens = await requestTokens(email, password);
      tokenStorage.set(tokens);
      try {
        queryClient.clear(); // jangan pernah mewarisi cache user sebelumnya
        setUser(await fetchMe());
      } catch (error) {
        tokenStorage.clear();
        throw error;
      }
    },
    [queryClient],
  );

  const logout = useCallback(async () => {
    const refresh = tokenStorage.getRefresh();
    tokenStorage.clear();
    queryClient.clear(); // data organisasi tidak boleh tertinggal di cache
    setUser(null);
    if (refresh) {
      try {
        await requestLogout(refresh); // cabut refresh token di server
      } catch {
        // pass
      }
    }
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({ user, isLoading, login, logout }),
    [user, isLoading, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}