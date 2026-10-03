type AbortableRequestCallbacks<T> = {
  onStart?: () => void;
  onSuccess: (value: T) => void;
  onError: (error: unknown) => void;
  onFinally?: () => void;
};

export function runAbortableRequest<T>(
  execute: (signal: AbortSignal) => Promise<T>,
  callbacks: AbortableRequestCallbacks<T>,
): { abort: () => void; done: Promise<void> } {
  const controller = new AbortController();

  const started = new Promise<void>((resolve) => {
    queueMicrotask(() => {
      if (!controller.signal.aborted) callbacks.onStart?.();
      resolve();
    });
  });

  const done = (async () => {
    await started;
    if (controller.signal.aborted) return;
    try {
      const value = await execute(controller.signal);
      if (!controller.signal.aborted) callbacks.onSuccess(value);
    } catch (error: unknown) {
      if (!controller.signal.aborted) callbacks.onError(error);
    } finally {
      if (!controller.signal.aborted) callbacks.onFinally?.();
    }
  })();

  return {
    abort: () => controller.abort(),
    done,
  };
}
