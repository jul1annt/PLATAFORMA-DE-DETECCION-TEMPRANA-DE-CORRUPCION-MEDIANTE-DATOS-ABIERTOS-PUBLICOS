import axios from 'axios';
import { clearStoredToken, getStoredToken } from '../authStorage';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

const isLoginRequest = (url?: string): boolean =>
  (url ?? '').split('?')[0].replace(/\/+$/, '').endsWith('/api/auth/login');

const bearerTokenFromHeader = (authorization: unknown): string | null => {
  if (typeof authorization !== 'string') return null;
  return authorization.match(/^Bearer\s+(\S+)$/i)?.[1] ?? null;
};

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  const hasExplicitAuthorization = Boolean(
    config.headers.get?.('Authorization') ?? config.headers.Authorization
  );
  if (token && !hasExplicitAuthorization && !isLoginRequest(config.url)) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: unknown) => {
    const requestConfig = axios.isAxiosError(error) ? error.config : undefined;
    const headers = requestConfig?.headers;
    const authorization = headers?.get?.('Authorization') ?? headers?.Authorization;
    const requestToken = bearerTokenFromHeader(authorization);
    if (
      axios.isAxiosError(error)
      && error.response?.status === 401
      && !isLoginRequest(requestConfig?.url)
      && requestToken
      && requestToken === getStoredToken()
    ) {
      clearStoredToken();
      window.dispatchEvent(new Event('auth:expired'));
    }
    return Promise.reject(error);
  },
);

export default api;
