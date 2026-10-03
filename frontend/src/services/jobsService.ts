import api from '../api/axios';
import type { BackgroundJobAccepted, BackgroundJobResponse } from '../types/api.generated';

export type BackgroundJobStatus = BackgroundJobResponse['status'];

export type BackgroundJobDTO<T = Record<string, unknown>> = Omit<BackgroundJobResponse, 'result'> & {
  result: T | null;
};

const delay = (milliseconds: number) => new Promise((resolve) => window.setTimeout(resolve, milliseconds));

export class JobContinuesError extends Error {
  readonly jobId: string;

  constructor(jobId: string) {
    super(`El trabajo sigue en segundo plano. Consulta /api/jobs/${jobId} para ver su estado.`);
    this.name = 'JobContinuesError';
    this.jobId = jobId;
  }
}

export const jobsService = {
  enqueue: async (path: string, payload: unknown): Promise<BackgroundJobAccepted> => {
    const response = await api.post<BackgroundJobAccepted>(path, payload);
    return response.data;
  },

  get: async <T,>(id: string): Promise<BackgroundJobDTO<T>> => {
    const response = await api.get<BackgroundJobResponse>(`/api/jobs/${id}`);
    return response.data as BackgroundJobDTO<T>;
  },

  waitForResult: async <T,>(id: string, timeoutMs = 30 * 60 * 1000): Promise<T> => {
    const deadline = Date.now() + timeoutMs;
    while (Date.now() < deadline) {
      const job = await jobsService.get<T>(id);
      if (job.status === 'EXITOSO' && job.result !== null) return job.result;
      if (job.status === 'PARCIAL' && job.result !== null) return job.result;
      if (job.status === 'ERROR') {
        throw new Error(job.error_message || `El trabajo falló. Referencia: ${job.error_id || id}`);
      }
      await delay(1500);
    }
    throw new JobContinuesError(id);
  },
};
