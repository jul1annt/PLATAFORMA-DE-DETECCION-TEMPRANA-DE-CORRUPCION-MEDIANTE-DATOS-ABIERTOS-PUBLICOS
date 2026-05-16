import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from 'react';
import toast from 'react-hot-toast';
import { authService } from '../services/authService';
import type { AdminResponse, LoginRequest } from '../types/auth';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AuthContextValue {
  admin: AdminResponse | null;
  token: string | null;
  loading: boolean;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

// ─── Storage key ─────────────────────────────────────────────────────────────

const TOKEN_KEY = 'admin_token';

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null);

// ─── Provider ────────────────────────────────────────────────────────────────

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [admin, setAdmin] = useState<AdminResponse | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // ── On mount: restore session from localStorage ──────────────────────────
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }

    authService
      .me(stored)
      .then((adminData) => {
        setToken(stored);
        setAdmin(adminData);
      })
      .catch(() => {
        // Token expired or invalid — clear storage
        localStorage.removeItem(TOKEN_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback(async (data: LoginRequest) => {
    const tokenResponse = await authService.login(data);
    const newToken = tokenResponse.access_token;

    const adminData = await authService.me(newToken);

    localStorage.setItem(TOKEN_KEY, newToken);
    setToken(newToken);
    setAdmin(adminData);
  }, []);

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    const currentToken = localStorage.getItem(TOKEN_KEY);
    if (currentToken) {
      try {
        await authService.logout(currentToken);
      } catch {
        // Even if the server call fails, clear the local session
      }
    }
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setAdmin(null);
    toast.success('Sesión cerrada correctamente');
  }, []);

  return (
    <AuthContext.Provider value={{ admin, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

// ─── Hook ─────────────────────────────────────────────────────────────────────

export const useAuth = (): AuthContextValue => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>');
  }
  return ctx;
};
