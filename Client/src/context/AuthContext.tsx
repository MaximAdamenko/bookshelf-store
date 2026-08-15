import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { fetchMe } from "../api/auth";
import { tokenStore } from "../api/client";
import type { UserPublic } from "../api/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

interface AuthContextValue {
  user: UserPublic | null;
  status: AuthStatus;
  isAdmin: boolean;
  completeLogin: (accessToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserPublic | null>(null);
  const [status, setStatus] = useState<AuthStatus>(() =>
    tokenStore.get() ? "loading" : "anonymous",
  );
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!tokenStore.get()) return;
    fetchMe()
      .then((me) => {
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        tokenStore.clear();
        setUser(null);
        setStatus("anonymous");
      });
  }, []);

  useEffect(() => {
    const onUnauthorized = () => {
      setUser(null);
      setStatus("anonymous");
      queryClient.clear();
    };
    window.addEventListener("auth:unauthorized", onUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", onUnauthorized);
  }, [queryClient]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      status,
      isAdmin: user?.role === "admin",
      completeLogin: async (accessToken: string) => {
        tokenStore.set(accessToken);
        const me = await fetchMe();
        setUser(me);
        setStatus("authenticated");
      },
      logout: () => {
        tokenStore.clear();
        setUser(null);
        setStatus("anonymous");
        queryClient.clear();
      },
    }),
    [user, status, queryClient],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
