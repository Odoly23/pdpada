// Lafex - klien web. Suara memakai Web Speech API bawaan browser (gratis, tanpa server suara).

// NB: teks Tetun ditulis sebaik mungkin dan perlu ditinjau penutur asli.
const I18N = {
  tet: {
    login_title: 'Tama ba Lafex', phone: 'Númeru telemóvel', pin: 'PIN (númeru 4-6)', login: 'Tama',
    learn: 'Lian atu aprende', explain_in: 'Esplika iha lian', start: 'Hahú aprende',
    access: 'Sosa asesu / uza kódigu', voucher: 'Kódigu vaucher', redeem: 'Uza kódigu',
    back: 'Fila fali', repeat: 'Repete', handsfree: 'Laiha liman (automátiku)', slow: 'Neineik', send: 'Haruka',
    tap: 'Klik botaun atu ko\'alia', listening: 'Hau rona...', thinking: 'Hanoin...', speaking: 'Tutór ko\'alia...',
    access_active: (d) => `Asesu to'o ${d}`, access_free: (n) => `Dalan gratis ohin loron: ${n}`,
    you: 'Ita', tutor: 'Tutór', fix: 'Koreksaun',
    phone_invalid: 'Númeru telemóvel Timor-Leste la loos (+670 7xxx xxxx).', pin_wrong: 'PIN sala.', pin_invalid: 'PIN tenke númeru 4-6.',
    voucher_unknown: 'Kódigu la existe.', voucher_used: 'Kódigu ne\'e uza tiha ona.', redeemed: 'Asesu aumenta ona!',
    no_access: 'Dalan gratis ohin remata. Uza kódigu vaucher atu kontinua.', daily_limit: 'Limite loron ida remata. Fila fali aban.',
    busy: 'Sistema okupadu. Koko fali.', tutor_failed: 'Sistema falla. Koko fali.', refused: 'Tutór la bele hatán ba ne\'e.',
    no_stt: 'Browser ne\'e la suporta rona lian. Hakerek de\'it.', no_stt_lang: 'Rona lian ba lian ne\'e seidauk iha. Hakerek de\'it.',
    no_voice: 'Aparellu ne\'e la iha lian ba lian ne\'e; tutór sei hatudu de\'it teksto.',
    no_speech: 'Hau la rona. Klik botaun fali.',
  },
  id: {
    login_title: 'Masuk ke Lafex', phone: 'Nomor ponsel', pin: 'PIN (4-6 angka)', login: 'Masuk',
    learn: 'Bahasa yang dipelajari', explain_in: 'Penjelasan dalam bahasa', start: 'Mulai belajar',
    access: 'Beli akses / pakai kode', voucher: 'Kode voucher', redeem: 'Pakai kode',
    back: 'Kembali', repeat: 'Ulangi', handsfree: 'Tanpa tangan (otomatis)', slow: 'Pelan', send: 'Kirim',
    tap: 'Tekan tombol untuk bicara', listening: 'Saya mendengarkan...', thinking: 'Berpikir...', speaking: 'Tutor berbicara...',
    access_active: (d) => `Akses sampai ${d}`, access_free: (n) => `Jatah gratis hari ini: ${n}`,
    you: 'Anda', tutor: 'Tutor', fix: 'Koreksi',
    phone_invalid: 'Nomor ponsel Timor-Leste tidak valid (+670 7xxx xxxx).', pin_wrong: 'PIN salah.', pin_invalid: 'PIN harus 4-6 angka.',
    voucher_unknown: 'Kode tidak ditemukan.', voucher_used: 'Kode ini sudah dipakai.', redeemed: 'Akses ditambahkan!',
    no_access: 'Jatah gratis hari ini habis. Pakai kode voucher untuk lanjut.', daily_limit: 'Batas harian tercapai. Lanjut besok.',
    busy: 'Sistem sibuk. Coba lagi.', tutor_failed: 'Sistem gagal. Coba lagi.', refused: 'Tutor tidak bisa menjawab itu.',
    no_stt: 'Browser ini tidak mendukung pengenalan suara. Silakan mengetik.', no_stt_lang: 'Pengenalan suara untuk bahasa ini belum tersedia. Silakan mengetik.',
    no_voice: 'Perangkat ini tidak punya suara untuk bahasa ini; tutor hanya menampilkan teks.',
    no_speech: 'Saya tidak mendengar. Tekan tombol lagi.',
  },
  pt: {
    login_title: 'Entrar no Lafex', phone: 'Número de telemóvel', pin: 'PIN (4-6 dígitos)', login: 'Entrar',
    learn: 'Língua a aprender', explain_in: 'Explicações em', start: 'Começar',
    access: 'Comprar acesso / usar código', voucher: 'Código de voucher', redeem: 'Usar código',
    back: 'Voltar', repeat: 'Repetir', handsfree: 'Mãos livres (automático)', slow: 'Devagar', send: 'Enviar',
    tap: 'Toque no botão para falar', listening: 'Estou a ouvir...', thinking: 'A pensar...', speaking: 'O tutor está a falar...',
    access_active: (d) => `Acesso até ${d}`, access_free: (n) => `Turnos grátis hoje: ${n}`,
    you: 'Você', tutor: 'Tutor', fix: 'Correção',
    phone_invalid: 'Número de Timor-Leste inválido (+670 7xxx xxxx).', pin_wrong: 'PIN errado.', pin_invalid: 'O PIN deve ter 4-6 dígitos.',
    voucher_unknown: 'Código não encontrado.', voucher_used: 'Este código já foi usado.', redeemed: 'Acesso adicionado!',
    no_access: 'Os turnos grátis de hoje acabaram. Use um voucher para continuar.', daily_limit: 'Limite diário atingido. Continue amanhã.',
    busy: 'Sistema ocupado. Tente de novo.', tutor_failed: 'Falha no sistema. Tente de novo.', refused: 'O tutor não pode responder a isso.',
    no_stt: 'Este browser não reconhece voz. Escreva, por favor.', no_stt_lang: 'Ainda não há reconhecimento de voz para esta língua. Escreva, por favor.',
    no_voice: 'Este aparelho não tem voz para esta língua; o tutor só mostra texto.',
    no_speech: 'Não ouvi nada. Toque no botão outra vez.',
  },
  en: {
    login_title: 'Sign in to Lafex', phone: 'Mobile number', pin: 'PIN (4-6 digits)', login: 'Sign in',
    learn: 'Language to learn', explain_in: 'Explanations in', start: 'Start learning',
    access: 'Buy access / use code', voucher: 'Voucher code', redeem: 'Use code',
    back: 'Back', repeat: 'Repeat', handsfree: 'Hands-free (automatic)', slow: 'Slow', send: 'Send',
    tap: 'Press the button to speak', listening: 'Listening...', thinking: 'Thinking...', speaking: 'Tutor is speaking...',
    access_active: (d) => `Access until ${d}`, access_free: (n) => `Free turns today: ${n}`,
    you: 'You', tutor: 'Tutor', fix: 'Correction',
    phone_invalid: 'Invalid Timor-Leste number (+670 7xxx xxxx).', pin_wrong: 'Wrong PIN.', pin_invalid: 'PIN must be 4-6 digits.',
    voucher_unknown: 'Code not found.', voucher_used: 'This code was already used.', redeemed: 'Access added!',
    no_access: 'Free turns are used up for today. Use a voucher to continue.', daily_limit: 'Daily limit reached. Continue tomorrow.',
    busy: 'System busy. Try again.', tutor_failed: 'System error. Try again.', refused: 'The tutor cannot answer that.',
    no_stt: 'This browser has no speech recognition. Please type.', no_stt_lang: 'Speech recognition is not available for this language yet. Please type.',
    no_voice: 'This device has no voice for this language; the tutor will show text only.',
    no_speech: 'I did not hear anything. Press the button again.',
  },
};

// Tetun belum punya suara TTS; pakai suara Portugis sebagai pendekatan terdekat.
const UI_VOICE = { tet: 'pt-PT', id: 'id-ID', pt: 'pt-PT', en: 'en-US' };

const $ = (id) => document.getElementById(id);
const store = {
  get: (k) => { try { return localStorage.getItem(k); } catch { return null; } },
  set: (k, v) => { try { localStorage.setItem(k, v); } catch { /* abaikan */ } },
  del: (k) => { try { localStorage.removeItem(k); } catch { /* abaikan */ } },
};

const S = {
  cfg: null, token: store.get('lafex.token'), user: null,
  ui: store.get('lafex.ui') || 'tet', lang: store.get('lafex.lang') || 'en',
  history: [], last: null, busy: false, recog: null, session: 0,
};
const t = (k, ...a) => {
  const v = (I18N[S.ui] && I18N[S.ui][k]) ?? I18N.id[k] ?? k;
  return typeof v === 'function' ? v(...a) : v;
};

async function api(path, body) {
  const res = await fetch('/api' + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'content-type': 'application/json', ...(S.token ? { authorization: 'Bearer ' + S.token } : {}) },
    body: body ? JSON.stringify(body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.error || 'error'), { status: res.status, data });
  return data;
}

function applyI18n() {
  document.documentElement.lang = S.ui === 'tet' ? 'tet' : S.ui;
  document.querySelectorAll('[data-i18n]').forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $('text-input').placeholder = t('send');
  if (S.user) renderAccess();
  if (!S.busy) setHint(t('tap'));
}

const show = (id) => {
  ['view-login', 'view-home', 'view-session'].forEach((v) => { $(v).hidden = v !== id; });
};
const setHint = (txt) => { $('mic-hint').textContent = txt; };

/* ---------- Suara ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let voices = [];
const loadVoices = () => { voices = window.speechSynthesis ? speechSynthesis.getVoices() : []; };
if (window.speechSynthesis) { loadVoices(); speechSynthesis.onvoiceschanged = loadVoices; }

const pickVoice = (lang) =>
  voices.find((v) => v.lang.replace('_', '-').toLowerCase() === lang.toLowerCase()) ||
  voices.find((v) => v.lang.toLowerCase().startsWith(lang.slice(0, 2).toLowerCase()));

function speak(text, lang) {
  return new Promise((resolve) => {
    if (!text || !window.speechSynthesis) return resolve();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = lang;
    u.rate = $('chk-slow').checked ? 0.7 : 0.95;
    const v = pickVoice(lang);
    if (v) u.voice = v;
    u.onend = u.onerror = () => resolve();
    try { speechSynthesis.speak(u); } catch { resolve(); } // jangan sampai alur belajar macet karena suara
  });
}

function listen(lang) {
  return new Promise((resolve, reject) => {
    const r = new SR();
    S.recog = r;
    r.lang = lang;
    r.interimResults = false;
    r.maxAlternatives = 1;
    let heard = '';
    r.onresult = (e) => { heard = e.results[0][0].transcript; };
    r.onerror = (e) => { if (e.error === 'no-speech' || e.error === 'aborted') return; reject(new Error(e.error)); };
    r.onend = () => { S.recog = null; resolve(heard); };
    r.start();
  });
}

const stopAll = () => {
  if (window.speechSynthesis) speechSynthesis.cancel();
  if (S.recog) { try { S.recog.abort(); } catch { /* abaikan */ } }
};

/* ---------- Tampilan ---------- */
function addBubble(role, text, extra) {
  const d = document.createElement('div');
  d.className = 'bubble ' + role;
  const p = document.createElement('div');
  p.textContent = text;
  d.append(p);
  if (extra) {
    const fx = document.createElement('div');
    fx.className = 'fix';
    fx.textContent = extra;
    d.append(fx);
  }
  $('chat').append(d);
  $('chat').scrollTop = $('chat').scrollHeight;
}

function renderAccess() {
  const u = S.user;
  $('access-line').textContent = u.active
    ? t('access_active', new Date(u.expiresAt).toLocaleString())
    : t('access_free', u.turnsLeft);
  $('status').textContent = u.phone;
}

function renderPlans() {
  $('plans').replaceChildren(...Object.values(S.cfg.plans).map((p) => {
    const li = document.createElement('li');
    li.textContent = `${p.label}: $${p.priceUsd}`;
    return li;
  }));
}

function fillSelects() {
  $('sel-lang').replaceChildren(...Object.entries(S.cfg.languages).map(([k, v]) => new Option(v.name + (k === 'tet' ? ' (beta)' : ''), k)));
  $('sel-ui').replaceChildren(...Object.entries(S.cfg.uiLangs).map(([k, v]) => new Option(v, k)));
  $('sel-lang').value = S.lang;
  $('sel-ui').value = S.ui;
}

/* ---------- Alur belajar ---------- */
function setBusy(on, hint) {
  S.busy = on;
  $('btn-mic').classList.toggle('busy', on);
  if (hint) setHint(hint);
}

async function tutorTurn(text) {
  const sid = S.session;
  setBusy(true, t('thinking'));
  let r;
  try {
    r = await api('/tutor', { lang: S.lang, uiLang: S.ui, history: S.history, text });
  } catch (err) {
    setBusy(false);
    const key = err.data?.error === 'no_access' || err.data?.error === 'daily_limit' ? err.data.error
      : err.message === 'busy' ? 'busy' : 'tutor_failed';
    setHint(t(key));
    if (err.data?.user) { S.user = err.data.user; renderAccess(); }
    if (key === 'no_access') {
      // Kembali ke beranda tempat voucher dimasukkan; pesan diumumkan lewat role="alert".
      S.session++; stopAll(); show('view-home'); renderAccess();
      $('buy').open = true;
      $('redeem-msg').textContent = t('no_access');
      $('voucher').focus();
    }
    return false;
  }
  if (sid !== S.session) return false;
  S.user = r.user;
  if (r.refused) { setBusy(false); setHint(t('refused')); return false; }

  S.history.push({ role: 'user', content: text || '(start)' });
  S.history.push({ role: 'assistant', content: r.reply });
  S.last = r;
  $('level-badge').textContent = r.level;
  addBubble('tutor', r.reply, [r.correction && `${t('fix')}: ${r.correction}`, r.explanation].filter(Boolean).join('\n'));
  await speakTurn(r, sid);
  return true;
}

async function speakTurn(r, sid) {
  setHint(t('speaking'));
  const target = S.cfg.languages[S.lang].tts;
  if (window.speechSynthesis && !pickVoice(target)) $('voice-warn').textContent = t('no_voice');
  await speak(r.reply, target);
  if (sid !== S.session) return;
  // Koreksi dibacakan dengan suara bahasa target; penjelasan dengan suara bahasa penjelas.
  if (r.correction) await speak(r.correction, target);
  if (sid !== S.session) return;
  await speak(r.explanation, UI_VOICE[S.ui]);
  if (sid !== S.session) return;
  setBusy(false, t('tap'));
}

// Satu putaran: dengar -> kirim ke tutor -> bicara. Mode tanpa tangan mengulang otomatis.
async function cycle() {
  const sid = S.session;
  const stt = S.cfg.languages[S.lang].stt;
  if (!SR || !stt) { setHint(t(SR ? 'no_stt_lang' : 'no_stt')); $('text-input').focus(); return; }
  for (let miss = 0; miss < 2; miss++) {
    $('btn-mic').classList.add('on');
    setHint(t('listening'));
    let heard = '';
    try { heard = await listen(stt); } catch { heard = ''; }
    $('btn-mic').classList.remove('on');
    if (sid !== S.session) return;
    if (heard.trim()) { await submit(heard.trim()); return; }
    if (!$('chk-hands').checked) break;
  }
  setHint(t('no_speech'));
}

async function submit(text) {
  if (S.busy) return;
  if (/^(repeat|repete|ulangi|ulang|repetir)\b/i.test(text)) { await replay(); return; }
  addBubble('user', text);
  const ok = await tutorTurn(text);
  if (ok && $('chk-hands').checked && SR && S.cfg.languages[S.lang].stt) cycle();
}

async function replay() {
  if (!S.last) return;
  stopAll();
  const sid = S.session;
  setBusy(true);
  await speakTurn(S.last, sid);
}

async function startSession() {
  S.session++;
  S.history = [];
  S.last = null;
  $('chat').replaceChildren();
  $('voice-warn').textContent = S.lang === 'tet' ? t('no_stt_lang') : '';
  $('level-badge').textContent = S.user.levels[S.lang] || 'A1';
  show('view-session');
  setBusy(false, t('tap'));
  // Penting: browser hanya mengizinkan suara setelah interaksi pengguna; klik "Mulai" sudah cukup.
  const ok = await tutorTurn('');
  if (ok && $('chk-hands').checked && SR && S.cfg.languages[S.lang].stt) cycle();
}

/* ---------- Peristiwa ---------- */
$('btn-login').onclick = async () => {
  $('login-msg').textContent = '';
  try {
    const r = await api('/auth', { phone: $('phone').value, pin: $('pin').value });
    S.token = r.token; S.user = r.user;
    store.set('lafex.token', r.token);
    show('view-home'); renderAccess();
  } catch (err) { $('login-msg').textContent = t(err.message); }
};

$('btn-redeem').onclick = async () => {
  $('redeem-msg').textContent = '';
  try {
    const r = await api('/redeem', { code: $('voucher').value });
    S.user = r.user; renderAccess();
    $('voucher').value = '';
    $('redeem-msg').textContent = t('redeemed');
  } catch (err) { $('redeem-msg').textContent = t(err.message); }
};

$('sel-lang').onchange = (e) => { S.lang = e.target.value; store.set('lafex.lang', S.lang); };
$('sel-ui').onchange = (e) => { S.ui = e.target.value; store.set('lafex.ui', S.ui); applyI18n(); };
$('btn-start').onclick = startSession;
$('btn-back').onclick = () => { S.session++; stopAll(); setBusy(false); $('btn-mic').classList.remove('on'); show('view-home'); renderAccess(); };
$('btn-repeat').onclick = replay;

$('btn-mic').onclick = () => {
  if (S.recog) { S.recog.stop(); return; }
  if (S.busy) { stopAll(); setBusy(false, t('tap')); return; }
  cycle();
};

$('text-form').onsubmit = (e) => {
  e.preventDefault();
  const v = $('text-input').value.trim();
  if (!v) return;
  $('text-input').value = '';
  submit(v);
};

// Spasi = tombol bicara (membantu pengguna keyboard / pembaca layar).
document.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && !$('view-session').hidden && !['INPUT', 'BUTTON', 'SELECT'].includes(document.activeElement.tagName)) {
    e.preventDefault();
    $('btn-mic').click();
  }
});

/* ---------- Awal ---------- */
(async () => {
  S.cfg = await api('/config');
  fillSelects(); renderPlans(); applyI18n();
  if (S.token) {
    try { S.user = await api('/me'); show('view-home'); renderAccess(); applyI18n(); return; }
    catch { S.token = null; store.del('lafex.token'); }
  }
  show('view-login');
})();
