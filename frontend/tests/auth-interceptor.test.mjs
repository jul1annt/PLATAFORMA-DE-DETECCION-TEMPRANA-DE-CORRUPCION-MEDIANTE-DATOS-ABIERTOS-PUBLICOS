import assert from 'node:assert/strict';
import { after, afterEach, before, beforeEach, test } from 'node:test';
import axios, { AxiosError } from 'axios';
import { createServer } from 'vite';

const stored = new Map();
const authEvents = [];
globalThis.localStorage = {
  getItem: (key) => stored.get(key) ?? null,
  setItem: (key, value) => stored.set(key, String(value)),
  removeItem: (key) => stored.delete(key),
};
globalThis.window = {
  dispatchEvent: (event) => {
    authEvents.push(event.type);
    return true;
  },
};

let vite;
let api;
let authStorage;
let originalAdapter;

before(async () => {
  vite = await createServer({
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
    appType: 'custom',
  });
  ({ default: api } = await vite.ssrLoadModule('/src/api/axios.ts'));
  authStorage = await vite.ssrLoadModule('/src/authStorage.ts');
  originalAdapter = api.defaults.adapter;
});

after(async () => {
  await vite?.close();
});

beforeEach(() => {
  stored.clear();
  authEvents.length = 0;
  api.defaults.adapter = async (config) => {
    const response = {
      config,
      data: { detail: 'expired' },
      headers: {},
      status: 401,
      statusText: 'Unauthorized',
    };
    throw new AxiosError(
      'Unauthorized',
      'ERR_BAD_REQUEST',
      config,
      undefined,
      response,
    );
  };
});

afterEach(() => {
  api.defaults.adapter = originalAdapter;
});

test('a 401 from an old token does not expire a newer login', async () => {
  authStorage.storeToken('new-token');

  await assert.rejects(
    api.get('/api/procesados/logs', {
      headers: { Authorization: 'Bearer old-token' },
    }),
    (error) => axios.isAxiosError(error) && error.response?.status === 401,
  );

  assert.equal(authStorage.getStoredToken(), 'new-token');
  assert.deepEqual(authEvents, []);
});

test('a 401 from the currently stored token expires the session', async () => {
  authStorage.storeToken('current-token');

  await assert.rejects(
    api.get('/api/procesados/logs', {
      headers: { Authorization: 'Bearer current-token' },
    }),
    (error) => axios.isAxiosError(error) && error.response?.status === 401,
  );

  assert.equal(authStorage.getStoredToken(), null);
  assert.deepEqual(authEvents, ['auth:expired']);
});

test('a login 401 does not expire a previously stored session', async () => {
  authStorage.storeToken('existing-token');

  await assert.rejects(
    api.post('/api/auth/login', { username: 'admin', password: 'wrong' }),
    (error) => axios.isAxiosError(error) && error.response?.status === 401,
  );

  assert.equal(authStorage.getStoredToken(), 'existing-token');
  assert.deepEqual(authEvents, []);
});
