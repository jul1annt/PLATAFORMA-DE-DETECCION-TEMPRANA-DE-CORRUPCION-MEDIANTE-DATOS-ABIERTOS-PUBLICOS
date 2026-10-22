import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import toast from 'react-hot-toast';
import { authService } from '../services/authService';
import type { AdminResponse, LoginRequest } from '../types/auth';
import { clearStoredToken, getStoredToken, storeToken } from '../authStorage';
import { AuthContext } from './authContextDefinition';
import { getErrorMessage } from '../utils/errors';

// ─── Types ────────────────────────────────────────────────────────────────────

// ─── Provider ────────────────────────────────────────────────────────────────

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [initialToken] = useState(getStoredToken);
  const [admin, setAdmin] = useState<AdminResponse | null>(null);
  const [token, setToken] = useState<string | null>(initialToken);
  const [loading, setLoading] = useState(Boolean(initialToken));
  const [restoreError, setRestoreError] = useState<string | null>(null);
  const [restoreAttempt, setRestoreAttempt] = useState(0);
  const sessionVersion = useRef(0);

  // ── On mount: restore session from localStorage ──────────────────────────
  useEffect(() => {
    if (!initialToken) return;

    const controller = new AbortController();
    let active = true;
    const restoreVersion = sessionVersion.current;
    authService
      .me(initialToken, controller.signal)
      .then((adminData) => {
        if (
          active
          && sessionVersion.current === restoreVersion
          && getStoredToken() === initialToken
        ) {
          setAdmin(adminData);
        }
      })
      .catch((error: unknown) => {
        if (
          active
          && !controller.signal.aborted
          && sessionVersion.current === restoreVersion
          && getStoredToken() === initialToken
        ) {
          setRestoreError(getErrorMessage(error, 'No fue posible verificar la sesión.'));
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [initialToken, restoreAttempt]);

  const retrySessionRestore = useCallback(() => {
    if (!getStoredToken()) return;
    setRestoreError(null);
    setLoading(true);
    setRestoreAttempt((attempt) => attempt + 1);
  }, []);

  useEffect(() => {
    const expire = () => {
      sessionVersion.current += 1;
      clearStoredToken();
      setToken(null);
      setAdmin(null);
      setLoading(false);
      setRestoreError(null);
    };
    window.addEventListener('auth:expired', expire);
    return () => window.removeEventListener('auth:expired', expire);
  }, []);

  // ── Login ─────────────────────────────────────────────────────────────────
  const login = useCallback(async (data: LoginRequest) => {
    const requestVersion = ++sessionVersion.current;
    const tokenResponse = await authService.login(data);
    const newToken = tokenResponse.access_token;

    const adminData = await authService.me(newToken);
    if (sessionVersion.current !== requestVersion) return;

    storeToken(newToken);
    setToken(newToken);
    setAdmin(adminData);
    setRestoreError(null);
  }, []);

  // ── Logout ────────────────────────────────────────────────────────────────
  const logout = useCallback(async () => {
    const currentToken = getStoredToken();
    sessionVersion.current += 1;
    clearStoredToken();
    setToken(null);
    setAdmin(null);
    setLoading(false);
    setRestoreError(null);
    if (currentToken) {
      try {
        await authService.logout(currentToken);
      } catch {
        // Even if the server call fails, clear the local session
      }
    }
    toast.success('Sesión cerrada correctamente');
  }, []);

  return (
    <AuthContext.Provider value={{ admin, token, loading, restoreError, retrySessionRestore, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
};
