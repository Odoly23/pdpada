import test from 'node:test';
import assert from 'node:assert/strict';
import os from 'node:os';
import path from 'node:path';
import fs from 'node:fs';

process.env.LAFEX_OFFLINE = '1';
process.env.LAFEX_DB = path.join(fs.mkdtempSync(path.join(os.tmpdir(), 'lafex-')), 'db.json');
process.env.FREE_TURNS_PER_DAY = '2';
process.env.TURNS_PER_DAY_PAID = '4';
process.env.ADMIN_TOKEN = 'secret';

const db = await import('../lib/db.js');
const { createServer } = await import('../server.js');
db.load();

const server = createServer();
await new Promise((r) => server.listen(0, r));
const base = `http://localhost:${server.address().port}/api`;
test.after(() => server.close());

const call = async (p, body, token, headers = {}) => {
  const res = await fetch(base + p, {
    method: body ? 'POST' : 'GET',
    headers: { 'content-type': 'application/json', ...(token ? { authorization: 'Bearer ' + token } : {}), ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  return { status: res.status, body: await res.json() };
};

let token;

test('hanya nomor Timor-Leste yang diterima', async () => {
  assert.equal((await call('/auth', { phone: '+62 812 3456 7890', pin: '1234' })).status, 400);
  assert.equal((await call('/auth', { phone: '771 2345', pin: '1234' })).status, 400); // 7 digit: terlalu pendek
  const ok = await call('/auth', { phone: '+670 7712 3456', pin: '1234' });
  assert.equal(ok.status, 200);
  token = ok.body.token;
});

test('PIN salah ditolak, PIN benar masuk lagi', async () => {
  assert.equal((await call('/auth', { phone: '+67077123456', pin: '9999' })).status, 401);
  assert.equal((await call('/auth', { phone: '67077123456', pin: '1234' })).status, 200);
});

test('tutor offline bekerja dan jatah gratis habis', async () => {
  let r = await call('/tutor', { lang: 'en', uiLang: 'tet', history: [], text: '' }, token);
  assert.equal(r.status, 200);
  assert.match(r.body.reply, /name/i);
  r = await call('/tutor', { lang: 'en', uiLang: 'tet', history: [{ role: 'user', content: '(start)' }, { role: 'assistant', content: r.body.reply }], text: 'Maria' }, token);
  assert.equal(r.status, 200);
  assert.ok(r.body.correction, 'jawaban satu kata harus dikoreksi');
  r = await call('/tutor', { lang: 'en', uiLang: 'tet', history: [], text: '' }, token);
  assert.equal(r.status, 402);
  assert.equal(r.body.error, 'no_access');
});

test('tanpa token ditolak', async () => {
  assert.equal((await call('/tutor', { lang: 'en' })).status, 401);
});

test('voucher sekali pakai membuka akses dan menambah waktu', async () => {
  assert.equal((await call('/admin/vouchers', { plan: '1d', count: 1 }, null, { 'x-admin-token': 'wrong' })).status, 403);
  const v = await call('/admin/vouchers', { plan: '1d', count: 2 }, null, { 'x-admin-token': 'secret' });
  const [a, b] = v.body.codes;

  const r1 = await call('/redeem', { code: a }, token);
  assert.equal(r1.status, 200);
  assert.equal(r1.body.user.active, true);
  const first = r1.body.user.expiresAt;

  assert.equal((await call('/redeem', { code: a }, token)).body.error, 'voucher_used');
  assert.equal((await call('/redeem', { code: 'NOPE' }, token)).body.error, 'voucher_unknown');

  const r2 = await call('/redeem', { code: b.toLowerCase() }, token);
  assert.ok(r2.body.user.expiresAt - first >= 24 * 3600 * 1000 - 1000, 'waktu harus ditambahkan');
});

test('akses aktif: tutor jalan sampai batas harian', async () => {
  // Jatah hari ini sudah terpakai 2 saat gratis (total batas berbayar 4) -> sisa 2.
  assert.equal((await call('/tutor', { lang: 'pt', uiLang: 'id', history: [], text: '' }, token)).status, 200);
  assert.equal((await call('/tutor', { lang: 'ko', uiLang: 'id', history: [], text: '' }, token)).status, 200);
  const r = await call('/tutor', { lang: 'ja', uiLang: 'id', history: [], text: '' }, token);
  assert.equal(r.status, 402);
  assert.equal(r.body.error, 'daily_limit');
});

test('bahasa tidak dikenal ditolak', async () => {
  assert.equal((await call('/tutor', { lang: 'xx' }, token)).status, 400);
});

test('berkas statis dan perlindungan path traversal', async () => {
  const origin = base.replace('/api', '');
  assert.equal((await fetch(origin + '/')).status, 200);
  assert.equal((await fetch(origin + '/app.js')).status, 200);
  const evil = await fetch(origin + '/..%2f..%2fetc%2fpasswd');
  assert.notEqual(evil.status, 200);
});
