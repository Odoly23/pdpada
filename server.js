import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import Anthropic from '@anthropic-ai/sdk';
import * as db from './lib/db.js';
import { tutorTurn, mode } from './lib/tutor.js';
import {
  PLANS, LANGUAGES, UI_LANGS, LEVELS, TURNS_PER_DAY_PAID, FREE_TURNS_PER_DAY,
} from './lib/config.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const PUBLIC = path.join(here, 'public');
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || '';

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.json': 'application/json',
};

const send = (res, status, body) => {
  res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-store' });
  res.end(JSON.stringify(body));
};

function readJson(req) {
  return new Promise((resolve, reject) => {
    let size = 0;
    const chunks = [];
    req.on('data', (c) => {
      size += c.length;
      if (size > 64 * 1024) { reject(Object.assign(new Error('too_large'), { status: 413 })); req.destroy(); return; }
      chunks.push(c);
    });
    req.on('end', () => {
      try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {}); }
      catch { reject(Object.assign(new Error('bad_json'), { status: 400 })); }
    });
    req.on('error', reject);
  });
}

// Pembatas laju sederhana per IP (anti-penyalahgunaan dasar).
const hits = new Map();
function rateLimited(ip, max = 60, windowMs = 60_000) {
  const now = Date.now();
  const rec = (hits.get(ip) || []).filter((t) => now - t < windowMs);
  rec.push(now);
  hits.set(ip, rec);
  return rec.length > max;
}

const authUser = (req) => {
  const m = (req.headers.authorization || '').match(/^Bearer (\w+)$/);
  return m ? db.userByToken(m[1]) : null;
};

function publicUser(phone, user) {
  return {
    phone,
    active: db.isActive(user),
    expiresAt: user.expiresAt || 0,
    levels: user.levels,
    turnsLeft: db.turnsLeft(user, TURNS_PER_DAY_PAID, FREE_TURNS_PER_DAY),
  };
}

function cleanHistory(h) {
  if (!Array.isArray(h)) return [];
  const out = h
    .filter((m) => m && (m.role === 'user' || m.role === 'assistant') && typeof m.content === 'string' && m.content.trim())
    .slice(-20)
    .map((m) => ({ role: m.role, content: m.content.slice(0, 1000) }));
  while (out.length && out[0].role !== 'user') out.shift(); // API: pesan pertama harus user
  return out;
}

async function handleApi(req, res, url) {
  const ip = req.socket.remoteAddress || '';
  if (rateLimited(ip)) return send(res, 429, { error: 'rate_limited' });

  if (req.method === 'GET' && url.pathname === '/api/config') {
    return send(res, 200, {
      plans: PLANS, languages: LANGUAGES, uiLangs: UI_LANGS, levels: LEVELS,
      freeTurns: FREE_TURNS_PER_DAY, paidTurns: TURNS_PER_DAY_PAID, mode: mode(),
    });
  }

  if (req.method === 'POST' && url.pathname === '/api/auth') {
    const { phone, pin } = await readJson(req);
    const p = db.normalizePhone(phone);
    if (!p) return send(res, 400, { error: 'phone_invalid' });
    const r = db.authenticate(p, String(pin ?? ''));
    if (r.error) return send(res, r.error === 'pin_wrong' ? 401 : 400, { error: r.error });
    return send(res, 200, { token: r.token, user: publicUser(p, db.userByToken(r.token).user) });
  }

  if (req.method === 'POST' && url.pathname === '/api/admin/vouchers') {
    if (!ADMIN_TOKEN || req.headers['x-admin-token'] !== ADMIN_TOKEN) return send(res, 403, { error: 'forbidden' });
    const { plan, count } = await readJson(req);
    const n = Math.min(Math.max(parseInt(count, 10) || 1, 1), 500);
    if (!PLANS[plan]) return send(res, 400, { error: 'plan_unknown' });
    return send(res, 200, { codes: db.createVouchers(plan, n) });
  }

  const auth = authUser(req);
  if (!auth) return send(res, 401, { error: 'unauthorized' });
  const { phone, user } = auth;

  if (req.method === 'GET' && url.pathname === '/api/me') return send(res, 200, publicUser(phone, user));

  if (req.method === 'POST' && url.pathname === '/api/redeem') {
    const { code } = await readJson(req);
    const r = db.redeem(phone, code);
    if (r.error) return send(res, 400, { error: r.error });
    return send(res, 200, { user: publicUser(phone, user) });
  }

  if (req.method === 'POST' && url.pathname === '/api/tutor') {
    const body = await readJson(req);
    const lang = LANGUAGES[body.lang] ? body.lang : null;
    const uiLang = UI_LANGS[body.uiLang] ? body.uiLang : 'tet';
    if (!lang) return send(res, 400, { error: 'lang_invalid' });
    const text = String(body.text || '').trim().slice(0, 1000);
    const history = cleanHistory(body.history);

    if (!db.consumeTurn(user, TURNS_PER_DAY_PAID, FREE_TURNS_PER_DAY)) {
      return send(res, 402, { error: db.isActive(user) ? 'daily_limit' : 'no_access', user: publicUser(phone, user) });
    }
    const level = user.levels[lang] || 'A1';
    try {
      const r = await tutorTurn({ lang, uiLang, history, text, level });
      if (r.refused) return send(res, 200, { reply: '', refused: true, level, user: publicUser(phone, user) });
      if (r.level !== level) db.setLevel(user, lang, r.level);
      return send(res, 200, { ...r, user: publicUser(phone, user) });
    } catch (err) {
      // Kembalikan jatah giliran jika AI gagal; bukan salah siswa.
      user.usage.turns = Math.max(0, user.usage.turns - 1);
      console.error('tutor error:', err instanceof Anthropic.APIError ? `${err.status} ${err.message}` : err);
      if (err instanceof Anthropic.RateLimitError) return send(res, 503, { error: 'busy' });
      return send(res, 502, { error: 'tutor_failed' });
    }
  }

  return send(res, 404, { error: 'not_found' });
}

function serveStatic(req, res, url) {
  const rel = url.pathname === '/' ? 'index.html' : decodeURIComponent(url.pathname).replace(/^\/+/, '');
  const file = path.normalize(path.join(PUBLIC, rel));
  if (!file.startsWith(PUBLIC + path.sep)) { res.writeHead(403); return res.end(); }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); return res.end('not found'); }
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}

export function createServer() {
  return http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x');
    try {
      if (url.pathname.startsWith('/api/')) await handleApi(req, res, url);
      else serveStatic(req, res, url);
    } catch (err) {
      send(res, err.status || 500, { error: err.message || 'server_error' });
    }
  });
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  db.load();
  const port = Number(process.env.PORT || 3000);
  createServer().listen(port, () => {
    console.log(`Lafex jalan di http://localhost:${port}  (tutor: ${mode()})`);
    if (!ADMIN_TOKEN) console.log('ADMIN_TOKEN belum diatur; buat voucher lewat: npm run vouchers -- 7d 5');
  });
}
