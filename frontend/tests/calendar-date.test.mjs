import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { createServer } from 'vite';

let vite;
let formatCalendarDate;

before(async () => {
  vite = await createServer({
    configFile: false,
    logLevel: 'silent',
    server: { middlewareMode: true },
    appType: 'custom',
  });
  ({ formatCalendarDate } = await vite.ssrLoadModule('/src/utils/format.ts'));
});

after(async () => {
  await vite?.close();
});

test('calendar dates retain their day in western and eastern time zones', () => {
  const previousZone = process.env.TZ;
  try {
    for (const zone of ['UTC', 'America/Bogota', 'Pacific/Auckland']) {
      process.env.TZ = zone;
      assert.equal(formatCalendarDate('2024-06-01'), '1/6/2024', zone);
      assert.equal(formatCalendarDate('2024-02-29'), '29/2/2024', zone);
      assert.equal(formatCalendarDate('2024-12-31'), '31/12/2024', zone);
      assert.equal(formatCalendarDate('2024-06-01', 'en-US'), '6/1/2024', zone);
    }
  } finally {
    if (previousZone === undefined) delete process.env.TZ;
    else process.env.TZ = previousZone;
  }
});

test('missing, malformed and impossible calendar dates show the fallback', () => {
  for (const value of [undefined, null, '', '2024-2-01', '2023-02-29',
    '2024-04-31', '2024-13-01', '2024-00-01', '2024-06-00',
    '2024-06-01T00:00:00Z', 'not-a-date']) {
    assert.equal(formatCalendarDate(value), 'N/A', String(value));
  }
});
