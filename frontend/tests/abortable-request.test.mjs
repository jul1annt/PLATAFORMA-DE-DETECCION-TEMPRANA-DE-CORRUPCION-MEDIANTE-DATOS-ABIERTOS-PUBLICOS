import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let vite;
let runAbortableRequest;

before(async () => {
  vite = await createServer({
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
    appType: 'custom',
  });
  ({ runAbortableRequest } = await vite.ssrLoadModule('/src/utils/abortableRequest.ts'));
});

after(async () => {
  await vite?.close();
});

function deferred() {
  let resolve;
  const promise = new Promise((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

test('a late response from an aborted search cannot overwrite the newer result', async () => {
  const oldResponse = deferred();
  const newResponse = deferred();
  const results = [];
  const errors = [];
  const settled = [];
  let oldSignal;

  const oldRequest = runAbortableRequest(
    (signal) => {
      oldSignal = signal;
      return oldResponse.promise;
    },
    {
      onSuccess: (value) => results.push(value),
      onError: (error) => errors.push(error),
      onFinally: () => settled.push('old'),
    },
  );
  await new Promise((resolve) => setTimeout(resolve, 0));
  oldRequest.abort();

  const newRequest = runAbortableRequest(
    () => newResponse.promise,
    {
      onSuccess: (value) => results.push(value),
      onError: (error) => errors.push(error),
      onFinally: () => settled.push('new'),
    },
  );

  newResponse.resolve('resultados nuevos');
  await newRequest.done;
  oldResponse.resolve('resultados antiguos');
  await oldRequest.done;

  assert.equal(oldSignal.aborted, true);
  assert.deepEqual(results, ['resultados nuevos']);
  assert.deepEqual(errors, []);
  assert.deepEqual(settled, ['new']);
});
