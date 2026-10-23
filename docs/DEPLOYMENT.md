# Public demo deployment

The public image uses only `data/public_raw/`, currently 22 statute chunks.
It does not copy `.env`, `.git`, the local HiKorea extracts, the original HWP,
local indexes, or evaluation output. Store secrets in your host's environment
settings. The Docker build does not need a Gemini key.

## Build and run

```bash
docker build -t korea-visa-rag .
docker volume create visa-data
docker run --rm -p 8000:8000 -v visa-data:/var/lib/visarag \
  -e SEARCH_ONLY=true korea-visa-rag
```

Named Docker volumes inherit the image directory's app-user ownership. A host
bind mount must be writable by the image's `app` user. On a hosting service,
attach a writable persistent disk at `/var/lib/visarag`, expose `$PORT`, and use
`/api/health` as its health check. The image runs one worker as a non-root user.
No public host or demo URL has been provisioned yet.

Startup creates keyword-search chunks without embedding calls. With a Gemini
key and no completed embedding cache, answers use keyword retrieval and health
advertises only `bm25`. Semantic and combined search appear only after a matching
complete index exists. Set `SEARCH_ONLY=true` for a fully free deployment.

## Enable Gemini

Store only `GEMINI_API_KEY` and the desired `GEMINI_CHAT_MODEL` /
`GEMINI_EMBED_MODEL` in the host environment. Do not upload your entire local
`.env`, which can contain unrelated credentials such as a Telegram bot token.
Run this explicit preparation job with the same persistent volume and environment:

```bash
python scripts/build_index.py
```

Then restart the web process. Model name and source content determine the index
directory. Unchanged vectors are reused; an interrupted build resumes missing
batches. A source or model change gets a separate directory, leaving the old
cache intact. Delete old index generations manually only when no running process
uses them. Do not run concurrent preparation jobs against the same volume.

## Usage limits

Defaults are 20 requests per client per minute, 100 AI requests per UTC day for
the deployment, and two concurrent AI operations. Configure these with
`API_REQUESTS_PER_MINUTE`, `API_DAILY_AI_REQUESTS`, and `API_MAX_CONCURRENT_AI`.
The SQLite usage ledger lives on the persistent disk. Failed paid operations
consume a reservation. A hybrid answer can make both an embedding query and a
chat request, so this is a request budget, not a monetary cap. Set provider-side
billing limits separately. Output is capped at 1,536 tokens per answer.

`/api/search` also reserves paid usage when it uses semantic retrieval. Health
checks use no provider requests. Provider quota, timeout, connection and empty
response failures return safe messages instead of raw SDK errors.

The server ignores forwarded-IP headers. Behind a reverse proxy, clients can
share one rate-limit bucket. Configure per-user limits at the hosting edge if
needed; do not trust arbitrary client-supplied IP headers. Run one app instance.
Multiple replicas would need a shared rate-limit service and coordinated storage.
These limits are suitable for a small demo, not a general public API service.

## Verification status

The local suite exercises real FastAPI, Chroma, Kiwi and BM25 without API keys.
The statute-only app passed local health, homepage, keyword-search and real
Gemini-answer smoke checks. Free mode passed with provider calls disabled.
Desktop and mobile rendering were checked, and the README screenshot is a real
local statute-only answer.
`.github/workflows/container.yml` builds the image, checks secret canaries are
excluded, starts keyless, then tests health, the homepage and a cited search.
Docker is unavailable on the current development machine, so container execution
and the new CI workflow remain unverified until run on a Docker-enabled host.
No GitHub Actions result is claimed before that run passes.

Keep the project marked "In development" until a public URL is deployed and its
health, sources, limits, English/Korean replies and persistent cache are checked.
