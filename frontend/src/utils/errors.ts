import axios from 'axios';

interface ApiErrorBody {
  detail?: string;
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    return error.response?.data?.detail || error.message || fallback;
  }

  return error instanceof Error ? error.message : fallback;
}
