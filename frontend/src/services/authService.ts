// ─── Auth Service ─────────────────────────────────────────────────────────────
// JWT is only attached explicitly on the two endpoints that require it:
//   POST /api/auth/logout  → logout()
//   GET  /api/auth/me      → me()
// All other calls have NO Authorization header.

import api from '../api/axios';
import type {
  LoginRequest,
  TokenResponse,
  AdminResponse,
  MessageResponse,
} from '../types/auth';

export const authService = {
  /**
   * POST /api/auth/login
   * No JWT required.
   */
  login: async (data: LoginRequest): Promise<TokenResponse> => {
    const response = await api.post<TokenResponse>('/api/auth/login', data);
    return response.data;
  },

  /**
   * GET /api/auth/me
   * JWT required — token is passed explicitly per-call.
   */
  me: async (token: string): Promise<AdminResponse> => {
    const response = await api.get<AdminResponse>('/api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  },

  /**
   * POST /api/auth/logout
   * JWT required — token is passed explicitly per-call.
   */
  logout: async (token: string): Promise<MessageResponse> => {
    const response = await api.post<MessageResponse>(
      '/api/auth/logout',
      {},
      { headers: { Authorization: `Bearer ${token}` } }
    );
    return response.data;
  },
};
