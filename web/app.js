// One shared RAG API; presentation and source inspection stay in the browser.
const $ = (selector) => document.querySelector(selector);
const messages = $('#messages');
const input = $('#question');
const form = $('#ask-form');
const sendBtn = $('#send');
const showText = $('#show-text');
const status = $('#status');
const modeNames = { bm25: 'Keyword search', vector: 'Meaning search', hybrid: 'Combined search' };
const sourceSets = new Map();
let nextAnswer = 0;
let currentSources = null;
let searchOnly = true;
let serverHealth = null;
const DOCUMENT_ICON = '<svg viewBox="0 0 24 28" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M4 2h10l6 6v18H4z"/><path d="M14 2v7h6M8 13h8M8 17h8M8 21h5"/></svg>';

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[character]);
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null;
  } catch { return null; }
}

// Escape before adding our limited formatting. Only real source numbers become buttons.
function formatAnswer(text, sourceNumbers = []) {
  return escapeHtml(text).trim().split(/\n{2,}/).map((block) => {
    // A model can put prose and a list in the same paragraph block.
    const groups = [];
    for (const line of block.split('\n')) {
      const item = line.match(/^\s*([-*•]|\d+\.)\s+(.+)$/);
      const tag = item ? 'ul' : 'p';
      if (groups.at(-1)?.tag !== tag) groups.push({ tag, lines: [] });
      groups.at(-1).lines.push(item ? `<li>${item[2]}</li>` : line);
    }
    const html = groups.map(({ tag, lines }) => `<${tag}>${lines.join(tag === 'p' ? '<br>' : '')}</${tag}>`).join('');
    return html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\[(\d+)\]/g, (match, number) => sourceNumbers.includes(Number(number))
        ? `<button type="button" class="cite" data-source-number="${Number(number)}" aria-label="View source ${Number(number)}">[${Number(number)}]</button>`
        : match);
  }).join('');
}

function setMenu(open) {
  $('.app-shell').classList.toggle('menu-open', open);
  $('.workspace-content').inert = open && window.matchMedia('(max-width: 900px)').matches;
  if (open) $('#focus-question').focus();
  $('#menu-toggle').setAttribute('aria-expanded', String(open));
  $('#menu-toggle').setAttribute('aria-label', open ? 'Close search settings' : 'Open search settings');
}

function inspectSources(record, number, moveFocus = false) {
  currentSources = record;
  const cited = record.cited || [];
  const sources = record.sources;
  $('#source-count').textContent = sources.length
    ? `${cited.length} cited · ${sources.length} retrieved ${sources.length === 1 ? 'passage' : 'passages'}`
    : 'No supporting passages were found.';
  $('#expand-sources').hidden = sources.length === 0;
  const first = number || cited[0] || sources[0]?.n;
  $('#source-list').innerHTML = sources.length ? sources.map((source) => {
    const url = safeUrl(source.url);
    const isCited = cited.includes(source.n);
    return `<details class="source" data-source-id="${source.n}" ${showText.checked || source.n === first ? 'open' : ''}>
      <summary><span class="source-number">${source.n}</span><span class="source-title">${escapeHtml(source.citation)}<span class="source-cited">${isCited ? 'Cited in this answer' : 'Retrieved passage'}</span></span></summary>
      <pre class="passage">${escapeHtml(source.text)}</pre>
      ${url ? `<a class="source-link" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">Open official source <span aria-hidden="true">↗</span></a>` : '<p class="error-help">Source link unavailable.</p>'}
    </details>`;
  }).join('') : '<p class="sources-empty">Try a visa code or a more specific question. The selected sources may not cover this topic.</p>';
  if (moveFocus) {
    const selected = [...document.querySelectorAll('.source')].find((element) => Number(element.dataset.sourceId) === first);
    (selected?.querySelector('summary') || $('#evidence')).focus();
    if (window.matchMedia('(max-width: 900px)').matches) $('#evidence').scrollIntoView({ behavior: 'auto', block: 'start' });
    else selected?.scrollIntoView({ behavior: 'auto', block: 'nearest' });
  }
}

function renderAnswer(card, data) {
  // Normalize numbers before interpolating them into attributes; all prose is escaped.
  const sources = data.sources.map((source, index) => ({ ...source, n: index + 1 }));
  const cited = (data.cited || []).filter((number) => Number.isInteger(number) && number > 0 && number <= sources.length);
  const record = { sources, cited };
  sourceSets.set(card.dataset.answerId, record);
  const isSearch = data.mode === 'search-only';
  const answer = isSearch
    ? (sources.length ? 'Here are matching passages from official sources. Select a passage to read the original text.' : 'No matching passages found. Try a visa code or different Korean keywords.')
    : data.answer;
  const references = cited.length ? sources.filter((source) => cited.includes(source.n)) : sources;
  card.innerHTML = `<h2 class="answer-heading">${DOCUMENT_ICON}${isSearch ? 'Official source passages' : 'Answer from your sources'}</h2>
    <div class="answer${isSearch ? ' note' : ''}">${formatAnswer(answer, sources.map((source) => source.n))}</div>
    ${references.length ? `<div class="answer-sources">${references.map((source) => {
      const url = safeUrl(source.url);
      return `<div class="answer-source"><span class="citation-index">${source.n}</span>${url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(source.citation)} <span aria-hidden="true">↗</span></a>` : `<span>${escapeHtml(source.citation)}</span>`}</div>`;
    }).join('')}<button type="button" class="inspect-sources">View original passages →</button></div>` : ''}
    <span class="meta">${escapeHtml(isSearch ? 'Source search' : modeNames[data.mode] || 'Search')} · ${sources.length} ${sources.length === 1 ? 'passage' : 'passages'} · ${escapeHtml(data.latency_s)}s</span>`;
  inspectSources(record);
}

function setBusy(busy) {
  sendBtn.disabled = busy;
  messages.setAttribute('aria-busy', String(busy));
  document.querySelectorAll('[data-query]').forEach((button) => { button.disabled = busy; });
}

// Phones scroll the page; desktop keeps the conversation in its own pane.
function revealReply(bot) {
  if (window.matchMedia('(max-width: 900px)').matches) {
    bot.scrollIntoView({ behavior: 'auto', block: 'start' });
  } else messages.scrollTop = messages.scrollHeight;
}

function replyIsVisible(bot) {
  const rect = bot.getBoundingClientRect();
  const mobile = window.matchMedia('(max-width: 900px)').matches;
  const bounds = mobile ? { top: 64, bottom: form.getBoundingClientRect().top } : messages.getBoundingClientRect();
  return rect.bottom > bounds.top && rect.top < bounds.bottom;
}

async function ask(question) {
  if (sendBtn.disabled) return;
  $('#empty')?.remove();
  setMenu(false);
  const user = document.createElement('div');
  user.className = 'msg-user';
  user.textContent = question;
  messages.appendChild(user);
  const bot = document.createElement('div');
  bot.className = 'msg-bot';
  const card = document.createElement('div');
  card.className = 'card';
  card.dataset.answerId = String(++nextAnswer);
  card.innerHTML = '<div class="typing" role="status">Finding official sources…</div>';
  bot.appendChild(card);
  messages.appendChild(bot);
  setBusy(true);
  revealReply(bot);
  let followReply = false;
  try {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const response = await fetch('/api/ask', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, mode, source_only: searchOnly, ai_ack: $('#ai-ack').checked }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
    followReply = replyIsVisible(bot);
    renderAnswer(card, data);
  } catch (error) {
    followReply = replyIsVisible(bot);
    card.innerHTML = `<h2 class="answer-heading">We couldn't complete that question.</h2><p class="answer error">${escapeHtml(error.message)}</p><p class="error-help">Try again shortly. Keyword search can help if meaning search is unavailable.</p>`;
  } finally {
    setBusy(false);
    // Do not pull visitors back if they moved to an earlier answer or source.
    if (followReply) revealReply(bot);
    // Keep focus where the visitor moved it during the request.
    if (document.activeElement === sendBtn || document.activeElement === document.body) input.focus({ preventScroll: true });
  }
}

messages.addEventListener('click', (event) => {
  const trigger = event.target.closest('.cite, .inspect-sources');
  if (!trigger) return;
  const record = sourceSets.get(trigger.closest('.card').dataset.answerId);
  if (record) inspectSources(record, Number(trigger.dataset.sourceNumber) || undefined, true);
});
form.addEventListener('submit', (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (question.length < 2 || sendBtn.disabled) return;
  input.value = '';
  input.style.height = '';
  ask(question);
});
input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    form.requestSubmit();
  }
});
input.addEventListener('input', () => {
  input.style.height = '';
  input.style.height = `${Math.min(input.scrollHeight, 112)}px`;
});
document.querySelectorAll('[data-query]').forEach((button) => {
  button.addEventListener('click', () => ask(searchOnly ? button.dataset.localQuery : button.dataset.query));
});
showText.addEventListener('change', () => {
  document.querySelectorAll('.source').forEach((source) => { source.open = showText.checked; });
});
$('#menu-toggle').addEventListener('click', () => setMenu(!$('.app-shell').classList.contains('menu-open')));
$('#focus-question').addEventListener('click', () => { setMenu(false); input.focus(); });
window.addEventListener('resize', () => {
  if (!window.matchMedia('(max-width: 900px)').matches) setMenu(false);
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && $('.app-shell').classList.contains('menu-open')) {
    setMenu(false); $('#menu-toggle').focus();
  }
});
document.addEventListener('click', (event) => {
  if ($('.app-shell').classList.contains('menu-open') && !event.target.closest('#sidebar, #menu-toggle')) setMenu(false);
});

function refreshCapabilities() {
  if (!serverHealth) return;
  const data = serverHealth;
  searchOnly = !data.llm || !$('#ai-ack').checked;
  $('#privacy-choice').hidden = !data.llm;
  status.textContent = searchOnly ? 'Source search' : 'AI answers on';
  status.className = `pill ${searchOnly ? 'pill-muted' : 'pill-ok'}`;
  $('#search-help').textContent = searchOnly
    ? 'Keyword search is on. Use a visa code or Korean keywords. Enable AI answers below for English or Korean explanations.'
    : 'Ask in English or Korean. Follow every answer back to its official sources.';
  $('#mode-help').textContent = searchOnly ? 'Keyword search uses no AI calls.' : 'Choose how sources are found.';
  document.querySelectorAll('input[name="mode"]').forEach((radio) => {
    radio.disabled = !data.modes.includes(radio.value) || (searchOnly && radio.value !== 'bm25');
    if (radio.disabled && radio.checked) document.querySelector('input[value="bm25"]').checked = true;
  });
  $('#empty-title')?.replaceChildren(searchOnly ? 'Search the official visa sources' : 'What would you like to know?');
  $('#empty-help')?.replaceChildren(searchOnly
    ? 'Use a visa code or Korean keywords to read original passages. AI answers are optional.'
    : 'Explore Korean study, work and family visa categories. Start with a visa code or choose a topic.');
  input.placeholder = searchOnly ? 'Try D-10 체류기간 or E-9 비전문취업' : 'Ask about a Korean visa… / 비자 질문을 입력하세요';
}
$('#ai-ack').addEventListener('change', refreshCapabilities);
fetch('/api/health').then(async (response) => {
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || 'Health check unavailable');
  serverHealth = data;
  refreshCapabilities();
}).catch((error) => {
  status.textContent = 'Server not ready';
  status.className = 'pill pill-warn';
  status.title = error.message || '';
  $('#search-help').textContent = 'The server could not be reached. Refresh to reconnect, or try again shortly.';
});
