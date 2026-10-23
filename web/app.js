// Front end for the Korea Visa Assistant. Plain JavaScript, no build step.

const $ = (sel) => document.querySelector(sel);
const messages = $("#messages");
const form = $("#ask-form");
const input = $("#question");
const sendBtn = $("#send");
const showText = $("#show-text");
const status = $("#status");
const modeNames = { bm25: "Keyword search", vector: "Meaning search", hybrid: "Combined search" };

const BOT_ICON = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
  stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M12 3l7 3v5c0 5-3 8-7 10-4-2-7-5-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>`;

// Escape text before inserting it as HTML (answers and sources are untrusted text).
function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// Minimal formatting for LLM answers: paragraphs, "- " bullet lists, and [n] citation badges.
function formatAnswer(text) {
  const blocks = escapeHtml(text).trim().split(/\n{2,}/);
  return blocks.map((block) => {
    const lines = block.split("\n");
    const html = lines.every((l) => /^\s*([-*•]|\d+\.)\s+/.test(l))
      ? `<ul>${lines.map((l) => `<li>${l.replace(/^\s*([-*•]|\d+\.)\s+/, "")}</li>`).join("")}</ul>`
      : `<p>${lines.join("<br>")}</p>`;
    return html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
               .replace(/\[(\d+)\]/g, '<span class="cite">[$1]</span>');
  }).join("");
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : null;
}

function renderSources(sources, cited) {
  if (!sources.length) return "";
  const items = sources.map((s) => {
    const isCited = cited.includes(s.n);
    const url = safeUrl(s.url);
    const title = url
      ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener">${escapeHtml(s.citation)}</a>`
      : `<span>${escapeHtml(s.citation)}</span>`;
    return `
      <div class="source${isCited ? " cited" : ""}">
        <div class="source-head">
          <span class="num">${s.n}</span>${title}
          ${isCited ? '<span class="tag">cited</span>' : ""}
        </div>
        <pre class="passage" ${showText.checked ? "" : "hidden"}>${escapeHtml(s.text)}</pre>
      </div>`;
  }).join("");
  return `<div class="sources"><span class="label">Official sources</span>${items}</div>`;
}

function addUserMessage(text) {
  $("#empty")?.remove();
  const el = document.createElement("div");
  el.className = "msg-user";
  el.textContent = text;
  messages.appendChild(el);
}

function addBotMessage() {
  const el = document.createElement("div");
  el.className = "msg-bot";
  el.innerHTML = `<div class="avatar">${BOT_ICON}</div>
    <div class="card"><div class="typing" aria-label="Searching"><span></span><span></span><span></span></div></div>`;
  messages.appendChild(el);
  messages.scrollTop = messages.scrollHeight;
  return el.querySelector(".card");
}

function renderAnswer(card, data) {
  const searchOnly = data.mode === "search-only";
  const answer = searchOnly
    ? (data.sources.length
      ? "Here are matching passages from official guides. Open a source link to read the full guide."
      : "No matching passages found. Try a visa code or different Korean keywords.")
    : data.answer;
  const count = data.sources.length;
  const sourceLabel = count === 1 ? "passage" : "passages";
  const method = searchOnly ? "Guide search" : (modeNames[data.mode] || "Search");
  card.innerHTML = `
    <div class="answer${searchOnly ? " note" : ""}">${formatAnswer(answer)}</div>
    ${renderSources(data.sources, data.cited || [])}
    <span class="meta">${escapeHtml(method)} · ${count} ${sourceLabel} · ${escapeHtml(data.latency_s)}s</span>`;
}

async function ask(question) {
  addUserMessage(question);
  const card = addBotMessage();
  sendBtn.disabled = true;
  try {
    const mode = document.querySelector('input[name="mode"]:checked').value;
    const res = await fetch("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, mode }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `Request failed (${res.status})`);
    renderAnswer(card, data);
  } catch (err) {
    card.innerHTML = `<p class="answer error">${escapeHtml(err.message)}</p>`;
  } finally {
    sendBtn.disabled = false;
    messages.scrollTop = messages.scrollHeight;
    input.focus();
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (q.length < 2) return;
  input.value = "";
  ask(q);
});

document.querySelectorAll(".example").forEach((btn) =>
  btn.addEventListener("click", () => ask(btn.dataset.query || btn.textContent.trim())));

showText.addEventListener("change", () =>
  document.querySelectorAll(".passage").forEach((p) => (p.hidden = !showText.checked)));

// Show whether the server runs in full AI mode or free search-only mode,
// and disable retrieval modes that are not available.
fetch("/api/health")
  .then((r) => r.json().then((d) => ({ ok: r.ok, d })))
  .then(({ ok, d }) => {
    if (!ok) throw new Error(d.detail);
    status.textContent = d.llm ? "AI answers on" : "Guide search";
    status.className = `pill ${d.llm ? "pill-ok" : "pill-muted"}`;
    $("#search-help").textContent = d.llm
      ? "Ask in English or Korean. Answers include links to the official passages used."
      : "Keyword search is on. Use a visa code or Korean keywords to find original guide passages.";
    const meaningAvailable = d.modes.includes("vector");
    $("#mode-help").textContent = meaningAvailable
      ? "Choose how to find passages. This changes the search method, not the source documents."
      : "Meaning search is not enabled in this session, so meaning and combined search are unavailable.";
    if (!d.llm) {
      $("#empty-title")?.replaceChildren("Search the official visa guides");
      $("#empty-help")?.replaceChildren("Try a visa code or Korean keywords, such as D-10 체류기간. You will see original passages and source links, without an AI-written answer.");
      input.placeholder = "Try D-10 체류기간 or D-2 시간제 취업";
      $("#examples-title").textContent = "Try a search";
      document.querySelectorAll(".example").forEach((button) => {
        button.textContent = button.dataset.localExample;
        button.dataset.query = button.dataset.localQuery;
      });
      showText.checked = true;
      document.querySelectorAll(".passage").forEach((p) => (p.hidden = false));
    }
    document.querySelectorAll('input[name="mode"]').forEach((r) => {
      r.disabled = !d.modes.includes(r.value);
      if (r.disabled && r.checked) document.querySelector('input[value="bm25"]').checked = true;
    });
  })
  .catch((err) => {
    status.textContent = "Server not ready";
    status.className = "pill pill-warn";
    status.title = err.message || "";
  });
