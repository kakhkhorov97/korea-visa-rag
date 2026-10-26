// Security-sensitive browser rendering helpers, tested without keys or a server.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
function helpers(mobile = false) {
  const element = { addEventListener() {}, scrollHeight: 500, getBoundingClientRect: () => ({ top: 700, bottom: 800 }) };
  const context = { URL, window: { addEventListener() {}, matchMedia: () => ({matches: mobile}) }, document: { querySelector: () => element, querySelectorAll: () => [], addEventListener() {} }, fetch: () => new Promise(() => {}) };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync('web/app.js', 'utf8') + '\nthis.helpers = {escapeHtml, safeUrl, formatAnswer, revealReply, replyIsVisible};', context);
  return context.helpers;
}
test('untrusted answer and source labels are escaped before formatting', () => {
  const h = helpers();
  const html = h.formatAnswer('<img src=x onerror=alert(1)> **Safe** [1]', [1]);
  assert.ok(html.includes('&lt;img'));
  assert.ok(!html.includes('<img'));
  assert.ok(html.includes('<strong>Safe</strong>'));
  assert.ok(html.includes('data-source-number="1"'));
  assert.equal(h.escapeHtml('"<&\''), '&quot;&lt;&amp;&#39;');
});
test('only returned source numbers become citation buttons', () => {
  const html = helpers().formatAnswer('A supported claim [2]. Unknown [99].', [1,2]);
  assert.ok(html.includes('data-source-number="2"'));
  assert.ok(!html.includes('data-source-number="99"'));
  assert.ok(html.includes('[99]'));
});
test('source links reject executable and relative URLs', () => {
  const h = helpers();
  for (const value of ['javascript:alert(1)', 'data:text/html,bad', '/local', 'file:///secret']) assert.equal(h.safeUrl(value), null);
  assert.equal(h.safeUrl('https://www.law.go.kr/'), 'https://www.law.go.kr/');
});

test('mixed prose and lists render consecutive list items without raw bullet prefixes', () => {
  const html = helpers().formatAnswer('Requirements:\n* **First** [1]\n* <script>bad</script>\nFinal note.', [1]);
  assert.ok(html.startsWith('<p>Requirements:</p><ul><li><strong>First</strong>'));
  assert.ok(html.includes('<li>&lt;script&gt;bad&lt;/script&gt;</li></ul><p>Final note.</p>'));
});
test('mobile reply navigation uses the page and detects deliberate navigation away', () => {
  const h = helpers(true);
  let calls = 0;
  const bot = { scrollIntoView: () => { calls++; }, getBoundingClientRect: () => ({top: 100, bottom: 200}) };
  h.revealReply(bot);
  assert.equal(calls, 1);
  assert.equal(h.replyIsVisible(bot), true);
  bot.getBoundingClientRect = () => ({top: -200, bottom: 10});
  assert.equal(h.replyIsVisible(bot), false);
  bot.getBoundingClientRect = () => ({top: 750, bottom: 800});
  assert.equal(h.replyIsVisible(bot), false);
});
