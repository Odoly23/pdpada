// Konfigurasi paket akses. Harga dalam USD (Timor-Leste memakai dolar AS).
// Ubah di sini setelah melihat biaya nyata per pengguna.
export const PLANS = {
  '1d':  { label: '24 jam',  hours: 24,       priceUsd: 1 },
  '3d':  { label: '3 hari',  hours: 24 * 3,   priceUsd: 2 },
  '7d':  { label: '7 hari',  hours: 24 * 7,   priceUsd: 3 },
  '30d': { label: '1 bulan', hours: 24 * 30,  priceUsd: 8 },
  '365d':{ label: '1 tahun', hours: 24 * 365, priceUsd: 60 },
};

// Batas pemakaian wajar: setiap giliran bicara = 1 panggilan AI.
export const TURNS_PER_DAY_PAID = Number(process.env.TURNS_PER_DAY_PAID || 150);
export const FREE_TURNS_PER_DAY = Number(process.env.FREE_TURNS_PER_DAY || 5);

export const LANGUAGES = {
  en:  { name: 'English',    stt: 'en-US', tts: 'en-US' },
  pt:  { name: 'Português',  stt: 'pt-PT', tts: 'pt-PT' },
  es:  { name: 'Español',    stt: 'es-ES', tts: 'es-ES' },
  ko:  { name: '한국어',      stt: 'ko-KR', tts: 'ko-KR' },
  ja:  { name: '日本語',      stt: 'ja-JP', tts: 'ja-JP' },
  tet: { name: 'Tetun',      stt: null,    tts: 'pt-PT' }, // belum ada STT/TTS Tetun; beta
};

// Bahasa penjelasan (antarmuka) untuk siswa.
export const UI_LANGS = {
  tet: 'Tetun',
  id:  'Bahasa Indonesia',
  pt:  'Português',
  en:  'English',
};

export const LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'];
