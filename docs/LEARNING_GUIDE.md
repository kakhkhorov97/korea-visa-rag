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

- Get a free key at open.law.go.kr, put it in `.env`, run `python scripts/fetch_laws.py`.
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

**Exercise:** ask an English question in the app with mode = `bm25`, then `vector`. Notice BM25
fails across languages and vector search doesn't.

---

## Lesson 5: Hybrid search + generation (`reciprocal_rank_fusion`, `assistant.py`) (2 h)

- **RRF:** each retriever votes by rank (`1 / (60 + rank)`). Chunks both retrievers like rise to the top.
  It ignores raw scores, which live on different scales.
- Read `SYSTEM_PROMPT`. Every rule exists to prevent a failure: no citations, guessing, wrong language.
- `llm.chat` converts our message list into Gemini contents and a separate system instruction.
  It also maps Gemini token counts to the keys used by `Answer` and the evaluation script.
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
- Why `escapeHtml()` runs before `formatAnswer()`: answers and sources are untrusted text, so
  escaping first prevents HTML/script injection (XSS). Interviewers like this question.
- With no `GEMINI_API_KEY`, `/api/health` reports `"llm": false` and the UI switches to search-only mode.
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
