# AGENTS.md: project handoff for coding agents

## Project

**Korea Visa Assistant (체류자격 도우미)** by Sean Kakhkhorov. A portfolio project for AI/LLM job
applications at South Korean tech companies.

A citation-first RAG assistant that answers questions about Korean student and job-seeker visas
(D-2, D-4, D-10, E-7) in English or Korean, using only official government sources (Korean
immigration law from open.law.go.kr, plus HiKorea guides). Every claim cites its source; it says
"I don't know" when the sources don't cover a question.

- Repo: https://github.com/kakhkhorov97/korea-visa-rag (branches: `main`, `develop`)
- Python 3.11+, no front-end build step
- Two interfaces on one engine: a FastAPI web app and a Telegram bot

## Architecture

```
data/raw/*.txt  (YAML-like header: title, source_url, doc_type: law|guide, retrieved)
  → chunking.py: laws split per article (제N조 / 제N조의M), 항/호 kept together; guides split by heading
  → data/processed/chunks.jsonl
  → retrieval.py: BM25 (Kiwi tokenizer + visa-code tokens like "D-10", "E-7-1")
                  + vector (OpenAI embeddings in Chroma, data/index/)
                  + hybrid (Reciprocal Rank Fusion, k=60)
  → assistant.py: VisaAssistant.ask() → LLM answer with [n] citations
                  (or free "search-only" mode when OPENAI_API_KEY is unset: BM25 only, no LLM)
  → api.py (FastAPI + web/)   and   telegram_bot.py (python-telegram-bot, long polling)
```

## Files

```
src/visarag/
  config.py        all settings and paths; reads .env (HAS_OPENAI flag drives search-only mode)
  documents.py     load data/raw files + metadata header
  chunking.py      article-aware Korean law chunker, guide chunker, windowing
  tokenizer.py     Kiwi morphological tokenizer + visa-code extraction
  retrieval.py     BM25Retriever, VectorRetriever (Chroma), HybridRetriever, reciprocal_rank_fusion
  llm.py           OpenAI embed() and chat() wrappers (the only file that calls OpenAI)
  assistant.py     VisaAssistant, Answer (with to_dict), SYSTEM_PROMPT, search-only fallback
  metrics.py       hit@k, recall@k, reciprocal rank, summarize
  api.py           FastAPI: GET /api/health, POST /api/ask, GET /api/search; serves web/ at /
  telegram_bot.py  /start, /help, /mode; format_answer_html, truncate (4096 limit), parse_mode_arg
web/               index.html, styles.css, app.js (plain JS; escapes all text before rendering)
scripts/
  fetch_laws.py    downloads 출입국관리법 + 시행령 + 시행규칙 from open.law.go.kr (needs LAW_API_OC)
  build_index.py   chunk + embed (embeds only if OPENAI_API_KEY is set; --no-embed to skip)
  find_chunks.py   BM25 keyword search printing chunk IDs, used for labeling the eval set
eval/
  questions.jsonl  30 questions (27 in scope, 3 out of scope); "relevant" lists are EMPTY, not yet labeled
  LABELING.md      how to label them, with Korean search terms per topic
  run_eval.py      compares available retrieval modes; --answers also generates answers (needs key)
tests/
  test_pipeline.py      unit + API + Telegram formatting tests (no API key needed)
  fixtures/fake_law.txt clearly fake law text used only by tests
docs/
  LEARNING_GUIDE.md  lessons explaining each part (Sean is learning the codebase)
  images/            mockup.png goes here (design mockup); screenshot.png once the app runs
.github/workflows/tests.yml  runs pytest on every push
Dockerfile, requirements.txt, .env.example, .gitignore, LICENSE (MIT), README.md (English + Korean)
```

Run commands:
```bash
pip install -r requirements.txt
cp .env.example .env
python scripts/fetch_laws.py
python scripts/build_index.py
uvicorn visarag.api:app --reload --app-dir src     # http://localhost:8000, docs at /docs
PYTHONPATH=src python -m visarag.telegram_bot
pytest -q
python eval/run_eval.py
```

## Current status

Done: chunking, tokenizer, BM25/vector/hybrid retrieval, cited answers, search-only mode, FastAPI
web app, Telegram bot, evaluation scripts, 30 unlabeled eval questions, tests, CI, bilingual README.

**Never run with the real libraries yet.** The original build environment couldn't install
packages, so tests passed only against simplified stand-ins for kiwipiepy and rank-bm25, and the
FastAPI and Chroma tests were skipped. Expect small fixes on first real run. Specifically check:

1. `pytest -q` passes with real kiwipiepy, rank-bm25, chromadb, fastapi, httpx.
   - `test_tokenizer_strips_particles` and `test_bm25_finds_visa_code` depend on Kiwi's real
     output; adjust `KEEP_TAGS` in tokenizer.py if needed (don't weaken the tests' intent).
   - `VectorRetriever` uses `metadata={"hnsw:space": "cosine"}`; newer Chroma versions may want a
     different configuration API.
2. `scripts/fetch_laws.py`: the open.law.go.kr JSON field names (법령일련번호, 조문단위, 조문내용,
   항, 호, 항내용, 호내용, 조문여부) were written from documentation and not verified against a live
   response. Print one raw response and fix `find_law` / `article_lines` / `fetch_law_text` if needed.
   Confirm the saved files chunk into sensible 제N조 articles.
3. The web app in search-only mode (no OpenAI key): /api/health, asking a question, sources render.
4. Telegram bot connects and replies (needs TELEGRAM_BOT_TOKEN from @BotFather).
5. GitHub Actions run is green.

## Remaining work (in priority order)

1. Get everything above running and passing.
2. Sean adds `docs/images/mockup.png`; then take a real screenshot of the running app
   (`docs/images/screenshot.png`) and update the README image and caption.
3. Label `eval/questions.jsonl` following `eval/LABELING.md`, run `python eval/run_eval.py`,
   and fill the README "Results" table with the real numbers.
4. Add HiKorea guide documents for D-2, D-4, D-10, E-7 to `data/raw/` (format in data/raw/README.md).
5. Deploy a public demo (Docker on Render / Railway / Fly.io / Hugging Face Spaces), works keyless
   in search-only mode. Add the link to the README.
6. Optional upgrades: cross-encoder reranker (measure MRR before/after), Upstage Solar vs OpenAI
   comparison (change only llm.py), housing/lease rules as a second domain, KakaoTalk channel.

## Rules for agents

- **Do not commit or push** unless Sean explicitly asks. He handles git himself.
- **Never invent results, metrics, screenshots, or legal content.** README numbers must come from
  actually running `eval/run_eval.py`. Keep the "In development" status until it's deployed.
  Visa/legal text must come only from official sources with `source_url` and `retrieved` filled in.
- Don't label the eval set to favor a method; labels reflect which chunk truly answers each question.
- Never commit `.env` or API keys.
- Keep the free search-only mode working; cost matters for this project.
- Keep LLM calls isolated in `llm.py` and keep `VisaAssistant` interface-agnostic.
- Keep escaping untrusted text in web/app.js and telegram_bot.py.
- Add or update tests with each change; tests must not need API keys.
- Sean is learning from this code: keep it readable, keep the explanatory docstrings, and update
  `docs/LEARNING_GUIDE.md` and README when behavior changes. Briefly explain what you changed and why.
