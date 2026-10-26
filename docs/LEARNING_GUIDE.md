# Learning Guide: understand every part of this project

Work through these lessons in order. Lessons 1–6 work without a Gemini key (search-only mode);
the vector and AI-answer parts need one. Each one: read the file, run something, do the small exercise.
By the end you should be able to rebuild any part from scratch and defend every design choice in an
interview. **Do the exercises: changing code yourself is what turns "I have this repo" into "I built this."**

---

## Lesson 0: What is RAG? (30 min)

An LLM alone answers from memory, which can be outdated or invented. **RAG (Retrieval-Augmented
Generation)** first *retrieves* relevant text from your own documents, then asks the LLM to answer
*using only that text*. Three stages:

1. **Index**: split documents into chunks and make them searchable (once).
2. **Retrieve**: for each question, find the most relevant chunks.
3. **Generate**: give question + chunks to the LLM, ask for a cited answer.

Almost every "AI engineer" job in Korea right now involves building or improving this loop.

---

## Lesson 1: Data (`documents.py`, `scripts/fetch_laws.py`) (1–2 h)

- Start with the four included HiKorea guide extracts in `data/raw/`. These work without a
  law API account. Read `data/SOURCES.md` for their origin, version and license.
- Get a free key at open.law.go.kr, put it in `.env`, run `python scripts/fetch_laws.py`.
  This is optional and adds laws alongside the guides.
- Open `data/raw/immigration_act_decree.txt`. Notice the 제N조 / ①② / 1. 2. structure.
- Why metadata matters: `source_url` and `retrieved` are what make citations possible.
- The loader preserves URL anchors such as `#article-2`. Inline metadata comments start
  with whitespace followed by `#`, so they do not remove the anchor from a citation link.

**Exercise:** copy one HiKorea page about D-10 into a `.txt` file with the header from `data/raw/README.md`.

---

## Lesson 2: Chunking (`chunking.py`) (2 h)

- Run `python scripts/build_index.py --no-embed` and look at `data/processed/chunks.jsonl`.
- Read `ARTICLE_RE`. Paste it into regex101.com with some law text and see what it matches.
- Key idea: **chunk boundaries should follow meaning.** One article = one rule = one chunk.

**Exercise:** change the code to split by fixed 500-character windows instead. Later, in Lesson 6,
compare evaluation scores. This experiment is a great résumé line ("article-based chunking improved hit@5 by X%").

**Interview question:** *"How did you choose your chunk size?"* → Explain article-based splitting and show your experiment.

---

## Lesson 3: Keyword search (`tokenizer.py`, `BM25Retriever`) (2 h)

- BM25 scores chunks by how often query words appear, weighted so rare words count more.
- Try in Python:
  ```python
  from visarag.tokenizer import tokenize
  tokenize("D-10 비자를 연장하려면 어떻게 하나요?")
  ```
  See how particles disappear and "D-10" stays whole.
- Run `python scripts/find_chunks.py "시간제 취업"`.

**Exercise:** replace `tokenize` with `text.split()` and see how results get worse on Korean questions.

**Interview question:** *"Why not just split on spaces?"* → Korean is agglutinative; particles attach to nouns.

---

## Lesson 4: Vector search (`VectorRetriever`, `llm.embed`) (2 h)

- An **embedding** turns text into a list of numbers where similar meanings are close together.
  That's why an English question can find a Korean article.
- Chroma stores those vectors and finds the nearest ones (cosine similarity).
- `llm.embed` uses Gemini's `RETRIEVAL_DOCUMENT` task for stored passages;
  `llm.embed_query` uses `RETRIEVAL_QUERY` for questions. Both use `gemini-embedding-001`.
  Rebuild the index if you change embedding providers or models.
- Indexing sends five passages per embedding request to reduce quota bursts. Google can
  still limit the project; a 429 response means the request was rejected by a quota limit.

**Exercise:** ask an English question in the app with mode = `bm25`, then `vector`. Notice BM25
fails across languages and vector search doesn't.

---

## Lesson 5: Hybrid search + generation (`reciprocal_rank_fusion`, `assistant.py`) (2 h)

- **RRF:** each retriever votes by rank (`1 / (60 + rank)`). Chunks both retrievers like rise to the top.
  It ignores raw scores, which live on different scales.
- Read `SYSTEM_PROMPT`. Every rule exists to prevent a failure: no citations, guessing, wrong language.
- `llm.chat` converts our message list into Gemini contents and a separate system instruction.
  It also maps Gemini token counts to the keys used by `Answer` and the evaluation script.
- The default answer model is `gemini-3.5-flash-lite`. The cached SDK client limits each
  request to 60 seconds with automatic retries disabled, so a stalled request returns control.
- `cited_numbers` checks which sources the answer actually used; the UI marks them ✅.

**Exercise:** delete rule 3 from the prompt and ask "What is the E-9 visa?" (not in your data).
Watch it start guessing. Put the rule back. This is how you learn why guardrails matter.

---

## Lesson 6: Evaluation (`metrics.py`, `eval/run_eval.py`) (3–4 h) ← most important

The `--k` argument controls how many top results count toward hit@k and recall@k.
It defaults to 5. Zero and negative values are rejected before questions or the index load.

1. For each question in `eval/questions.jsonl`, run `find_chunks.py` and copy the correct
   chunk IDs into `"relevant"`. Add your own questions until you have **30+** (half Korean, half English).
2. Run `python eval/run_eval.py`. You'll get a table for bm25 / vector / hybrid.
3. Run `python eval/run_eval.py --answers`, open the results JSON, and grade each answer by hand.
4. Put the numbers in the README Results table.

**Interview question:** *"How do you know your RAG system works?"* Most candidates can't answer.
You'll have a table.

---

## Lesson 7: The web app (`api.py`, `web/`) (2–3 h)

- Run `uvicorn visarag.api:app --reload --app-dir src` and open http://localhost:8000/docs.
  FastAPI generated that page from the `AskRequest` model. Try `/api/ask` from there.
- In `web/app.js`, follow one question: `ask()` → `fetch("/api/ask")` → `renderAnswer()`.
- The optional **Search options** panel uses friendly labels: Keyword search = `bm25`,
  Meaning search = `vector`, Combined search = `hybrid`. The API still uses those original
  mode values. In local mode, the UI explains the Korean keyword limitation and shows
  original passages by default. Provider setup instructions stay out of the result cards.
- Why `escapeHtml()` runs before `formatAnswer()`: answers and sources are untrusted text, so
  escaping first prevents HTML/script injection (XSS). Interviewers like this question.
- With no `GEMINI_API_KEY`, `/api/health` reports `"llm": false` and the UI switches to search-only mode.
- `SEARCH_ONLY=true` forces the same local mode even when a Gemini key is saved. Restart
  the server after editing `.env`. This also skips embedding calls when building the index.
- `AskRequest.strip_question` runs before length validation. A question containing only spaces
  gets HTTP 422 instead of reaching retrieval. Valid questions lose surrounding whitespace.
- `/api/search` uses `BeforeValidator(str.strip)` to trim `q` before checking its 2 to 500
  character length. Invalid queries get HTTP 422 before the assistant loads.

**Exercise:** add a "Copy answer" button to each answer card.

### Part 2: the Telegram bot (`telegram_bot.py`)

- Create a bot with @BotFather, add the token to `.env`, run `PYTHONPATH=src python -m visarag.telegram_bot`.
- Notice the bot reuses `VisaAssistant` unchanged. Separating the engine from the interface is
  the main architecture point to explain in interviews.
- `asyncio.to_thread(...)`: the bot is async, but `assistant.ask` blocks while calling Gemini.
  Running it in a thread keeps the bot responsive to other users meanwhile.
- `format_answer_html` escapes text before adding tags (same XSS idea as the web app) and
  `truncate` keeps replies under Telegram's 4,096-character limit.

**Exercise:** add a `/sources` command that resends the passages of the last answer.

---

## Lesson 8: Ship it (2–3 h)

- Push to GitHub (check `.env` is **not** committed).
- Deploy the Docker image to a host such as Render, Railway, Fly.io or Hugging Face Spaces (Docker);
  add `GEMINI_API_KEY` as a secret, or leave it out to run in free search-only mode.
- Record a 1-minute demo video. Write a velog post: problem → design → results → what you learned.

---

## Upgrades (each one = a résumé bullet with a number)

- Add a cross-encoder **reranker** after hybrid retrieval, measure the change in MRR.
- Compare **Upstage Solar** vs Gemini (only `llm.py` changes).
- Add a **FastAPI** endpoint so other apps can call it.
- Add housing / lease rules as a second domain.

---

## About presenting this project honestly

This project was built with AI assistance, which is normal in 2026 engineering. What interviewers
check is whether *you* understand it. Rule of thumb: if you can't explain a line, don't claim it.
Do the exercises, run the experiments yourself, and the results and decisions become genuinely yours.
If asked, say you used AI tools and then explain what you changed, measured and learned.

## Preparing a public demo

Local learning data and public deployment data now have separate paths.
`data/raw/` retains the HiKorea extracts. Docker copies only statutory text from
`data/public_raw/`. This prevents a guide's reuse restrictions from being
silently carried into the public image. See `data/public_raw/README.md` for the
source selection and provenance.

`VISARAG_RAW_DIR` selects the sources. `VISARAG_DATA_DIR` selects where generated
chunks, Chroma indexes and the API usage ledger live. On a host this should be a
persistent writable volume, so restarting the server retains the data.

Previously, startup deleted the index and embedded every chunk again. Now
`index_cache.py` hashes the model name and exact embedded text into a directory
name. `VectorRetriever.build()` compares stored IDs/text and embeds only missing
or changed chunks. An interrupted run can resume; a completed rerun costs no
embedding requests. `VisaAssistant` advertises vector/hybrid modes only after it
checks that the matching collection contains every current chunk. Startup runs
`build_index.py --no-embed`; enabling Gemini without a complete vector cache
still allows AI answers over keyword retrieval.

`limits.py` reserves API requests in SQLite before calling Gemini. The ledger
survives restarts. A semaphore bounds simultaneous paid operations. The app
hashes the actual connecting IP and ignores forwarded headers. Behind a proxy,
several visitors can share a limit. See `docs/DEPLOYMENT.md` for deployment
constraints. `llm.py` converts SDK errors to `ProviderError`, so the API can send
an actionable message without returning provider URLs or credentials.

The evaluation defaults to the public corpus. Every label has a source-based
note, and partial coverage stays in retrieval scoring. Retrieving a relevant
permission article does not prove the corpus contains all student-work rules.
A retrieval hit and a legally complete answer are different measurements.


`render.yaml` describes a proposed hosting service rather than provisioning it.
It specifies the Docker build, health endpoint, persistent disk, and secret
prompt. Keeping auto-deploys off lets Sean control when a pushed change goes
live. The Blueprint passes Render's published JSON schema; that validation does
not verify credentials, billing, disk permissions or a live service. The GitHub
container smoke test has now passed, while public deployment remains pending.


## Free hosting profile

The selected Render Blueprint now uses the Free plan and no persistent disk.
It enables `KIWI_LIGHTWEIGHT` to omit optional dictionaries while keeping the
real Korean analyzer. The local default is unchanged. Real-library regression
tests still check particle stripping and visa-code tokens.

Free hosting loses generated data and usage counters on restart. Startup builds
only free keyword chunks, so it cannot create embedding charges. With a Gemini
key the free server writes answers from keyword retrieval; without a key it
shows source passages. Use a Free-tier Gemini project if the whole demo must
cost nothing. Google quota limits remain separate from the app's counters.
The earlier paid-disk Blueprint description is superseded by this free profile.

## Cloud Run and persistent retrieval data

Cloud Run does not keep local files when an instance stops. A local Chroma
directory can therefore be a serving copy, but cannot be the durable index.
`scripts/export_snapshot.py` reads the reviewed public corpus and its existing
vectors into a JSON snapshot. It does not call Gemini. Private local documents
cannot be selected through this export command.

`snapshot.py` restores that snapshot into a fresh Chroma directory using the
saved vectors. Storage holds the persistent copy. Each cloud revision pins an
object generation and SHA-256 checksum, so replacing a bucket object cannot
silently change the running revision's sources. The importer also compares the
chunks to the public corpus in the image. A different corpus/model needs a new
image and matching snapshot. Startup fails if verification fails.

The usage ledger is different: it counts requests rather than storing retrieval
data. It remains temporary on Cloud Run, so its daily limit resets on instance
replacement. The proposed first deployment disables Gemini calls explicitly.
Paid AI needs a separately reviewed durable usage store and provider controls.
See [Google Cloud deployment](GOOGLE_CLOUD.md) for costs, identities, commands
and rollback. The subsequently approved private deployment passed live API and
two-revision index-restoration checks; details are in the
[release record](CLOUD_RELEASE_2026-10-25.md). Public access was subsequently enabled;
Gemini is now enabled using the existing Free-tier project. Cloud Run references
`visa-gemini-key:1` in Secret Manager; the key is never included in the image or
frontend. Switching `SEARCH_ONLY` off also makes the restored vector index
available, which enables meaning and combined search in the existing UI.

The expanded public corpus contains 21 visa-category definitions (39 chunks
including the existing articles and D-10 stay-limit excerpt). Complete annex
rows stay together, including F-2's continuation and F-3's exclusions. Category
definitions do not establish every subtype's eligibility, paperwork or points
threshold. The assistant must still abstain when those details are absent.
`scripts/extract_statute_annexes.py` pins the official PDF hash and reviewed row
boundaries; refreshing a changed PDF requires a new layout review.


## Modern web workspace

The frontend still calls the same FastAPI endpoints. The redesign changes the
layout and browser interaction, without changing retrieval or the Gemini prompt.
`web/app.js` stores each answer's sources separately, so clicking an older
citation opens that answer's original passages. All API text is escaped before
limited bold, list and citation formatting; source URLs accept only HTTP(S).

Desktop keeps the conversation and evidence in separate scrolling panes. On
phones, the page scrolls, search settings open in a drawer, and the composer
stays near the bottom. New replies scroll into view, but finishing a request
only follows it if the visitor has not moved away. The drawer makes the rest of
the workspace inert while open and closes with Escape.

Newsreader headings use a bundled font with its OFL license. IBM Plex Sans KR
continues to load from Google Fonts. Versioned CSS/JS URLs avoid stale assets
after a release. `node --test tests/test_web.cjs` checks escaping, source URLs,
list formatting and mobile reply navigation without an API key. `DESIGN.md`
and `.impeccable/design.json` record the implemented visual system.


## Keeping the answer language separate from sources

The retrieved sources are Korean even when the visitor asks in English. The
previous generic same-language instruction sometimes produced Korean replies.
`response_language()` now uses only the question, removing visa codes before
counting English and Korean word groups. Korean wins mixed-language ties;
code-only questions default to English. This is a small heuristic for the two
supported languages, so ambiguous mixed questions can still be classified badly.

`language_instruction()` adds the selected language to the system instruction
and repeats it after the question. Citation and source-only rules still apply.
`answer_matches_language()` compares Latin letters and Hangul after removing
parenthetical terms. It catches predominantly wrong-script responses while
allowing brief original terms. It is not a general language detector or a legal
accuracy check. A rejected reply raises a safe provider error with retry and
keyword-search guidance. There is no automatic repair call, so the request
limit still represents one answer-generation call. The extra instruction adds
some input tokens. Keyless source search is unchanged.
