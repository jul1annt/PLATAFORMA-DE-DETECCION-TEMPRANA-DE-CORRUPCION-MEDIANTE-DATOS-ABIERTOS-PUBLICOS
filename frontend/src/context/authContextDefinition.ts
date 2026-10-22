import { createContext } from 'react';
import type { AdminResponse, LoginRequest } from '../types/auth';

export interface AuthContextValue {
  admin: AdminResponse | null;
  token: string | null;
  loading: boolean;
  restoreError: string | null;
  retrySessionRestore: () => void;
  login: (data: LoginRequest) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
