import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';

// Server Anthropic palsu: merekam permintaan dan membalas dengan JSON terstruktur.
let seen;
const fake = http.createServer((req, res) => {
  let body = '';
  req.on('data', (c) => (body += c));
  req.on('end', () => {
    seen = JSON.parse(body);
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({
      id: 'msg_1', type: 'message', role: 'assistant', model: seen.model, stop_reason: 'end_turn', stop_sequence: null,
      content: [{ type: 'text', text: JSON.stringify({
        reply: 'Very good! What do you do?', correction: 'I am a student.',
        explanation: 'Gunakan "a" sebelum "student".', level: 'C2',
      }) }],
      usage: { input_tokens: 10, output_tokens: 10 },
    }));
  });
});
await new Promise((r) => fake.listen(0, r));
process.env.ANTHROPIC_BASE_URL = `http://localhost:${fake.address().port}`;
process.env.ANTHROPIC_API_KEY = 'test-key';
delete process.env.LAFEX_OFFLINE;
test.after(() => fake.close());

const { tutorTurn, mode } = await import('../lib/tutor.js');

test('mode AI aktif bila ada kunci', () => assert.match(mode(), /^ai:/));

test('permintaan ke Claude benar dan level dibatasi satu tingkat', async () => {
  const r = await tutorTurn({
    lang: 'en', uiLang: 'tet', level: 'A1', text: 'I student',
    history: [{ role: 'user', content: '(start)' }, { role: 'assistant', content: 'Hello! Who are you?' }],
  });
  assert.equal(seen.model, 'claude-opus-5-5');
  assert.equal(seen.output_config.format.type, 'json_schema');
  assert.equal(seen.output_config.format.schema.additionalProperties, false);
  assert.equal(seen.messages.at(-1).content, 'I student');
  assert.equal(seen.messages[0].role, 'user');
  assert.match(seen.system, /English/);
  assert.match(seen.system, /Tetun/);
  assert.equal(r.correction, 'I am a student.');
  assert.equal(r.level, 'A2', 'C2 diminta dari A1 -> hanya naik satu tingkat');
});

test('giliran pertama mengirim pesan pembuka sintetis', async () => {
  await tutorTurn({ lang: 'pt', uiLang: 'id', level: 'A1', text: '', history: [] });
  assert.equal(seen.messages.length, 1);
  assert.match(seen.messages[0].content, /baru saja datang/);
});
