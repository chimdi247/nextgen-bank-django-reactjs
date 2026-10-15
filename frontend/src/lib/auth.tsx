import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, onUnauthorized } from "./api";
import type { Role, User } from "./types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  /** Step 1: password. The server e-mails a one-time code (Mailpit in local docker). */
  requestOtp: (email: string, password: string) => Promise<void>;
  /** Step 2: code. Sets the auth cookies, then loads the user. */
  verifyOtp: (email: string, otp: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  isStaff: boolean;
  hasRole: (...roles: Role[]) => boolean;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      setUser(await api.get<User>("/auth/users/me/"));
    } catch {
      setUser(null);
    }
  }, []);

  // the session lives in HttpOnly cookies, so "am I signed in?" is answered by asking the API
  useEffect(() => { void refreshUser().finally(() => setLoading(false)); }, [refreshUser]);
  useEffect(() => { onUnauthorized(() => setUser(null)); }, []);

  const requestOtp = useCallback(async (email: string, password: string) => {
    await api.post("/auth/login/", { email, password });
  }, []);

  const verifyOtp = useCallback(async (email: string, otp: string) => {
    await api.post("/auth/verify-otp/", { email, otp });
    await refreshUser();
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try { await api.post("/auth/logout/", undefined, { noRefresh: true }); } catch { /* cookies may already be gone */ }
    setUser(null);
  }, []);

  const value = useMemo<AuthCtx>(() => ({
    user, loading, requestOtp, verifyOtp, logout, refreshUser,
    isStaff: !!user && user.role !== "customer",
    // a branch manager supervises every staff role (mirrors core_apps/common/permissions.py)
    hasRole: (...roles) => !!user && (roles.includes(user.role) || user.role === "branch_manager" || user.is_superuser),
  }), [user, loading, requestOtp, verifyOtp, logout, refreshUser]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside <AuthProvider>");
  return c;
}
