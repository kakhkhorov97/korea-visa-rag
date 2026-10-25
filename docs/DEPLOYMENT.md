# Public demo deployment

Google Cloud deployment is documented separately in
[GOOGLE_CLOUD.md](GOOGLE_CLOUD.md). A private search-only Cloud Run deployment
has passed its live checks; see the [release record](CLOUD_RELEASE_2026-10-25.md).
Public access remains pending approval. The Render configuration below remains
an alternative and has not been provisioned by this work.

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
Docker remains unavailable locally. GitHub Actions verified the pushed commit
`04f01644e0f6bc7ef6b8bb55cd7923de433c6809` on 2026-10-24 Asia/Seoul:

- Tests passed: https://github.com/kakhkhorov97/korea-visa-rag/actions/runs/39981558591
- Docker smoke test passed: https://github.com/kakhkhorov97/korea-visa-rag/actions/runs/39981558539

The subsequently prepared Render configuration has been validated locally
against https://render.com/schema/render.yaml.json. It still needs to be
committed/pushed by Sean if it will be deployed as a Git-based Blueprint.

Keep the project marked "In development" until a public URL is deployed and its
health, sources, limits, English/Korean replies and persistent cache are checked.


## Free Render deployment

Sean selected free hosting on 2026-10-24. `render.yaml` now uses `plan: free`,
one service in Singapore, and no disk. It keeps automatic redeploys off and
asks for the Gemini key as a secret, without storing a key in the repository.
No Render service has been created yet; the dashboard is waiting for sign-in.
This supersedes the earlier paid proposal.

Free web services sleep after 15 minutes without inbound traffic. Waking can
take about a minute. Their writable files are lost on sleep, restart or deploy.
Sources: https://render.com/docs/free and https://render.com/docs/compute-plans

Consequences for this demo:

- Startup rebuilds the 22 statute chunks for free. It makes no embedding calls.
- The free deployment has no saved vector cache. Gemini answers use BM25
  keyword retrieval. English questions can retrieve fewer useful passages than
  Korean keywords or visa codes. Semantic/hybrid search remains a local feature
  until an index and sufficient runtime memory are provided.
- Local API request counters reset when Render discards the filesystem. The
  advertised daily allowance is per instance lifetime within a UTC day, not a
  durable provider billing cap. Do not rely on it to cap a paid Gemini project.
- Use a Gemini project on Google's Free tier for a zero-cost AI demo. Free
  hosting does not make a billing-enabled Gemini key free. Do not enable paid
  billing as part of this deployment. Provider quota failures return readable
  errors. With no Gemini key, the app retains free search-only behavior.
- A free service still has bandwidth and build-minute allowances. Review the
  workspace's spend limit and avoid adding a payment method for this free demo.
  Render can suspend a service when free allowances run out.

Google billing information: https://ai.google.dev/gemini-api/docs/billing/

The Blueprint sets `KIWI_LIGHTWEIGHT=true`. This keeps the real Kiwi Korean
morphological model and base lexicon, but omits optional proper-name, typo and
multiword dictionaries and uses one tokenizer worker. Local defaults remain
unchanged. A local macOS measurement for the public search-only assistant was
346.8 MiB peak with this profile. Linux memory use and request peaks can differ.
The same 11-question BM25 evaluation produced hit@5 0.818, recall@5 0.636, MRR
0.818. See `eval/free_baseline.json` for the actual report.

The new container workflow applies a 512 MB memory cap with the lightweight
profile. It has not been pushed or run yet. The previously linked Docker pass
covers the earlier configuration, not this new free-hosting profile. Validate
this Blueprint with Render's published JSON schema before creation.

To deploy:

1. Sign in to https://dashboard.render.com/.
2. Sean commits and pushes the free configuration, or the reviewed settings
   are entered directly through the dashboard.
3. Create one Docker web service from the repository's `develop` branch,
   select Free, and confirm that no persistent disk or paid resources are listed.
4. Add the settings from `render.yaml`. Use only a confirmed Free-tier Gemini
   project key; otherwise leave the key absent for search-only operation.
5. Wait for Live. Verify `/api/health` reports 22 chunks, AI enabled when a key
   is supplied, and only `bm25` available. Test English/Korean questions and
   official source links, then add the actual public URL to README.
6. Verify a restart rebuilds free chunks without document embedding calls.

The paid-disk instructions earlier in this document remain an optional upgrade,
not the selected deployment. No paid resources may be created under this request.
