import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { PLANS } from './config.js';

const FILE = process.env.LAFEX_DB || path.join(process.cwd(), 'data', 'db.json');

let state = { users: {}, vouchers: {}, tokens: {} };

export function load() {
  try {
    state = JSON.parse(fs.readFileSync(FILE, 'utf8'));
  } catch {
    state = { users: {}, vouchers: {}, tokens: {} };
  }
}

function save() {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  const tmp = FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(state));
  fs.renameSync(tmp, FILE);
}

const today = () => new Date().toISOString().slice(0, 10);

// Hanya nomor seluler Timor-Leste: +670 7xxxxxxx
export function normalizePhone(raw) {
  const digits = String(raw || '').replace(/[\s\-()]/g, '').replace(/^\+/, '');
  const m = digits.match(/^(?:670)?(7\d{7})$/);
  return m ? '+670' + m[1] : null;
}

function hashPin(pin, salt) {
  return crypto.scryptSync(pin, salt, 32).toString('hex');
}

export function authenticate(phone, pin) {
  if (!/^\d{4,6}$/.test(String(pin))) return { error: 'pin_invalid' };
  let user = state.users[phone];
  if (!user) {
    const salt = crypto.randomBytes(16).toString('hex');
    user = state.users[phone] = {
      salt, pinHash: hashPin(pin, salt), expiresAt: 0, levels: {},
      usage: { date: today(), turns: 0 }, createdAt: Date.now(),
    };
  } else {
    const a = Buffer.from(hashPin(pin, user.salt), 'hex');
    const b = Buffer.from(user.pinHash, 'hex');
    if (!crypto.timingSafeEqual(a, b)) return { error: 'pin_wrong' };
  }
  const token = crypto.randomBytes(24).toString('hex');
  state.tokens[token] = phone;
  save();
  return { token };
}

export function userByToken(token) {
  const phone = state.tokens[token];
  return phone ? { phone, user: state.users[phone] } : null;
}

export function createVouchers(plan, count) {
  if (!PLANS[plan]) throw new Error('plano desconhecido: ' + plan);
  const codes = [];
  for (let i = 0; i < count; i++) {
    const code = crypto.randomBytes(5).toString('hex').toUpperCase().match(/.{1,4}/g).join('-');
    state.vouchers[code] = { plan, createdAt: Date.now(), usedBy: null, usedAt: null };
    codes.push(code);
  }
  save();
  return codes;
}

// Voucher sekali pakai. Jika akses masih aktif, waktunya ditambahkan.
export function redeem(phone, code) {
  const key = String(code || '').trim().toUpperCase();
  const v = state.vouchers[key];
  if (!v) return { error: 'voucher_unknown' };
  if (v.usedBy) return { error: 'voucher_used' };
  const user = state.users[phone];
  const base = Math.max(Date.now(), user.expiresAt || 0);
  user.expiresAt = base + PLANS[v.plan].hours * 3600 * 1000;
  v.usedBy = phone;
  v.usedAt = Date.now();
  save();
  return { expiresAt: user.expiresAt, plan: v.plan };
}

export function isActive(user) {
  return (user.expiresAt || 0) > Date.now();
}

// Mengembalikan false jika batas harian habis.
export function consumeTurn(user, paidLimit, freeLimit) {
  if (user.usage.date !== today()) user.usage = { date: today(), turns: 0 };
  const limit = isActive(user) ? paidLimit : freeLimit;
  if (user.usage.turns >= limit) return false;
  user.usage.turns++;
  save();
  return true;
}

export function turnsLeft(user, paidLimit, freeLimit) {
  if (user.usage.date !== today()) return isActive(user) ? paidLimit : freeLimit;
  return Math.max(0, (isActive(user) ? paidLimit : freeLimit) - user.usage.turns);
}

export function setLevel(user, lang, level) {
  user.levels[lang] = level;
  save();
}
