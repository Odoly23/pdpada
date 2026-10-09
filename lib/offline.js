// Tutor offline sederhana (tanpa AI) agar aplikasi tetap bisa dicoba tanpa kunci API.
// Isinya skrip pertanyaan dasar per bahasa. Kualitas jauh di bawah tutor AI.
const SCRIPTS = {
  en: [
    { q: 'Hello! Welcome to Lafex. What is your name?', model: 'My name is Maria.' },
    { q: 'Nice to meet you! Where are you from?', model: 'I am from Dili.' },
    { q: 'What do you do every day?', model: 'I work in the morning and study in the evening.' },
    { q: 'What food do you like?', model: 'I like fish and rice.' },
  ],
  pt: [
    { q: 'Olá! Bem-vindo ao Lafex. Como se chama?', model: 'Eu chamo-me Maria.' },
    { q: 'Muito prazer! De onde é?', model: 'Eu sou de Díli.' },
    { q: 'O que faz todos os dias?', model: 'Eu trabalho de manhã e estudo à noite.' },
    { q: 'De que comida gosta?', model: 'Eu gosto de peixe e arroz.' },
  ],
  es: [
    { q: '¡Hola! Bienvenido a Lafex. ¿Cómo te llamas?', model: 'Me llamo María.' },
    { q: '¡Mucho gusto! ¿De dónde eres?', model: 'Soy de Dili.' },
    { q: '¿Qué haces todos los días?', model: 'Trabajo por la mañana y estudio por la noche.' },
    { q: '¿Qué comida te gusta?', model: 'Me gusta el pescado y el arroz.' },
  ],
  ko: [
    { q: '안녕하세요! 라펙스에 오신 것을 환영합니다. 이름이 뭐예요?', model: '저는 마리아예요.' },
    { q: '만나서 반갑습니다. 어디에서 왔어요?', model: '저는 딜리에서 왔어요.' },
    { q: '매일 뭐 해요?', model: '아침에는 일하고 저녁에는 공부해요.' },
    { q: '무슨 음식을 좋아해요?', model: '저는 생선과 밥을 좋아해요.' },
  ],
  ja: [
    { q: 'こんにちは！ラフェックスへようこそ。お名前は何ですか？', model: '私はマリアです。' },
    { q: 'はじめまして。どこから来ましたか？', model: '私はディリから来ました。' },
    { q: '毎日、何をしますか？', model: '朝は働いて、夜は勉強します。' },
    { q: 'どんな食べ物が好きですか？', model: '私は魚とご飯が好きです。' },
  ],
  tet: [
    { q: 'Bondia! Ita nia naran saida?', model: 'Hau nia naran Maria.' },
    { q: 'Ita hela iha ne\'ebé?', model: 'Hau hela iha Dili.' },
    { q: 'Loron-loron ita halo saida?', model: 'Hau serbisu iha dader no estuda iha kalan.' },
    { q: 'Ita gosta han saida?', model: 'Hau gosta han ikan no fos.' },
  ],
};

const MSG = {
  tet: { good: 'Di\'ak! Kontinua.', retry: 'Koko fali ho sentensa kompletu.', hello: 'Ami hahú.' },
  id:  { good: 'Bagus! Lanjut.', retry: 'Coba lagi dengan kalimat lengkap.', hello: 'Kita mulai.' },
  pt:  { good: 'Muito bem! Continuamos.', retry: 'Tente outra vez com uma frase completa.', hello: 'Vamos começar.' },
  en:  { good: 'Good! Let\'s continue.', retry: 'Try again with a full sentence.', hello: 'Let\'s begin.' },
};

// Teks CJK tidak dipisah spasi, jadi ukur dengan jumlah karakter.
const isCjk = (lang) => lang === 'ko' || lang === 'ja';
const longEnough = (lang, text) =>
  isCjk(lang) ? text.replace(/\s/g, '').length >= 5 : text.trim().split(/\s+/).length >= 3;

export function offlineTutor({ lang, uiLang, history, text, level }) {
  const script = SCRIPTS[lang] || SCRIPTS.en;
  const msg = MSG[uiLang] || MSG.en;
  const asked = history.filter((m) => m.role === 'assistant').length;

  if (!text) {
    return { reply: script[0].q, correction: '', explanation: msg.hello, level: level || 'A1' };
  }

  const prev = script[Math.min(Math.max(asked - 1, 0), script.length - 1)];
  const ok = longEnough(lang, text);
  const next = script[asked % script.length];
  return ok
    ? { reply: next.q, correction: '', explanation: msg.good, level: level || 'A1' }
    : { reply: prev.q, correction: prev.model, explanation: msg.retry, level: level || 'A1' };
}
