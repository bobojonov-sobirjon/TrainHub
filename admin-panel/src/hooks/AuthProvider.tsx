import { useEffect, useMemo, useState, type ReactNode } from "react";
import { getMe, login, logout } from "../api/auth";
import type { UserPublic } from "../types/api";
import { AuthContext } from "./useAuth";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = sessionStorage.getItem("th_access");
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then(setUser)
      .catch(() => {
        sessionStorage.removeItem("th_access");
        sessionStorage.removeItem("th_refresh");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      signIn: async (loginValue: string, password: string) => {
        const tokens = await login(loginValue, password);
        sessionStorage.setItem("th_access", tokens.access_token);
        sessionStorage.setItem("th_refresh", tokens.refresh_token);
        setUser(tokens.user);
      },
      signOut: async () => {
        const refresh = sessionStorage.getItem("th_refresh");
        if (refresh) {
          try {
            await logout(refresh);
          } catch {
            /* ignore network errors on logout */
          }
        }
        sessionStorage.removeItem("th_access");
        sessionStorage.removeItem("th_refresh");
        setUser(null);
      },
    }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
