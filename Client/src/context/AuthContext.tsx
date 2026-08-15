import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { QueryClient } from "@tanstack/react-query";
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

// Catalog data is public; only user-scoped queries leave with the session.
// Clearing everything made every mounted page flash back to skeletons.
const PUBLIC_QUERY_KEYS = new Set(["books", "categories"]);

const dropPrivateQueries = (queryClient: QueryClient) =>
  queryClient.removeQueries({
    predicate: (query) => !PUBLIC_QUERY_KEYS.has(String(query.queryKey[0])),
  });

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
      dropPrivateQueries(queryClient);
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
        dropPrivateQueries(queryClient);
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
