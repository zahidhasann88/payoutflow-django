"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { ApiError, api } from "@/lib/api";
import type { ApiEnvelope, User } from "@/lib/types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isAdmin: boolean;
  isCreator: boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchCurrentUser(): Promise<User | null> {
  try {
    const res = await api.get<ApiEnvelope<User>>("/auth/me/");
    return res.data;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refreshUser = useCallback(async () => {
    setUser(await fetchCurrentUser());
    setLoading(false);
  }, []);

  useEffect(() => {
    let active = true;
    (async () => {
      const current = await fetchCurrentUser();
      if (!active) return;
      setUser(current);
      setLoading(false);
    })();
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setError(null);
    try {
      const res = await api.post<{ user: User }>("/auth/login/", { email, password });
      setUser(res.user);
      return res.user;
    } catch (e) {
      const message = e instanceof ApiError ? e.message : "Login failed.";
      setError(message);
      throw e;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await api.post("/auth/logout/", {});
    } catch {
      // best effort — the cookies are cleared server-side either way
    }
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      login,
      logout,
      refreshUser,
      isAdmin: user?.role === "ADMIN",
      isCreator: user?.role === "CREATOR",
    }),
    [user, loading, error, login, logout, refreshUser]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
