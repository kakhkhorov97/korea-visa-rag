# Expanded public corpus and Gemini activation

## Prepared locally

- 17 additional complete rows from the official Enforcement Decree annex:
  D-7, D-8, D-9; E-1 through E-6, E-8, E-9; F-1, F-2, F-3, F-4, F-6; H-1.
- Total: 39 public statute chunks and 21 broad visa categories. No HiKorea manual
  excerpts or private documents were added to the public package.
- Reused the existing 22 embeddings; generated only 17 new embeddings with the
  existing Free-tier Gemini project. The 39-vector index matches every chunk.
- Snapshot SHA-256:
  `3816ed4e3ba219116006f042e8cd995d35d38baf0031db13fe680ac6f15a8d08`.
  Snapshot size: 2,745,705 bytes. Startup restores saved vectors without API calls.
- `pytest -q`: 77 passed with real libraries. The production container build and
  its 1 GiB startup/health/homepage/source-search smoke checks passed.
- The refreshed 39-chunk retrieval evaluation is saved in
  `eval/public_expanded_baseline.json`. Existing labels were unchanged. They do
  not measure coverage or legal answer accuracy for the additional categories.
- Actual local Gemini checks retrieved and cited the F-3 definition in English
  and the E-9 definition in Korean. A weather question was refused, but the model
  answered that English question in Korean and attached irrelevant source
  citations to the refusal. Prompt rules do not guarantee perfect language or
  citation behavior; these checks are not an accuracy benchmark.

## Cloud status and remaining actions

The expanded release is **published with Gemini enabled** at
https://korea-visa-rag-jwq77bpivq-uc.a.run.app/.
Revision `korea-visa-rag-gemini39` receives 100% of visitor traffic. The
temporary test tag was removed. The homepage and F-6 result were verified in
the public browser. A screenshot is saved as `docs/images/cloud-run-expanded.jpg`.
The preceding search-only revision `korea-visa-rag-expanded39` is retained for
rollback with the same image and 39-chunk snapshot.

Secret Manager's `visa-gemini-key` secret exists. Only the runtime service
account has secretAccessor on that secret; the builder has no key access.
The user entered the existing key directly in Secret Manager. Version 1 was
confirmed enabled and pinned in the new revision. The key was not read back or
entered in chat, shell commands or build files.

Live Gemini candidate checks passed before moving traffic:

- Health reported 39 chunks, AI enabled and hybrid/BM25/vector available.
- English F-3 answer cited the complete dependent-category row.
- Korean E-9 answer cited the non-professional employment row and its exclusion.
- Vector search for H-1 returned the working-holiday category row.
- An English weather question in BM25 mode returned a refusal with no sources
  or citations. Earlier local hybrid-mode limitations remain documented above.
- Startup logs confirmed all 39 saved vectors restored from the pinned snapshot.

The temporary `geminicheck` tag was removed after routing 100% traffic to
`korea-visa-rag-gemini39`. Public browser checks showed "AI answers on" and all
three search controls enabled. No app code or container rebuild was needed for
this activation, and no paid Gemini billing was enabled.

Final public health confirmed AI enabled, all three retrieval modes and 39
chunks. The secret reference is pinned to version 1. CPU 1, memory 1 GiB,
concurrency 1, timeout 180 seconds and service/revision maximum 1 were preserved;
no positive minimum is configured. Public screenshot:
`docs/images/cloud-run-gemini.jpg`.

The additional public-browser F-3 answer displayed working citations but used
imprecise English: an awkward parenthetical conflated the F-2 reference and
F-3 category, and its abbreviated D-1-through-E-7 wording could include D-3,
which the row does not list. It also described an exclusion only as spouses.
This requires an answer-quality follow-up. The functional activation checks do
not establish legal accuracy; the source-only prompt is not a factual validator.

The reviewed upload archive is `/tmp/visa-release-20261026.zip`, SHA-256
`7d8176722e8891a908dfce8a77be293639bcb9ec980698277ef62ffc7ae87683`.
It includes only allowlisted app files, public statutes and the public snapshot.
The browser upload permission was enabled and the archive was uploaded to
Cloud Shell. Its hash and all 65 allowlisted paths were verified before
extraction into a new release folder. Cloud build and activation checks follow.

The new snapshot is stored in the existing private bucket at
`releases/3816ed4e3ba219116006f042e8cd995d35d38baf0031db13fe680ac6f15a8d08.json`,
generation `1792944324931553`. The build upload allowlist contains 63 files and
excludes the snapshot itself, credentials, local data and Git metadata.
Cloud Build ID: `a53b17e2-9b52-412b-af2c-c44bcdc4a504` (`us-central1`).
The build finished SUCCESS at 2026-10-25T16:08:26Z (2026-10-26 in Korea).
Image digest:
`sha256:42e82f54887958aed7cd499521b34be8feb27c203707a3d87fc676b93ebcfe7a`.
The candidate passed health (39 chunks, BM25, AI disabled), homepage and F-6,
E-9 and H-1 source searches. Every returned source URL was official law.go.kr.
Startup logs confirmed the pinned snapshot digest, 39 chunks and saved vectors.
Only then was visitor traffic moved to `korea-visa-rag-expanded39`.
After publication, a separate check confirmed 100% traffic, public health with
39 chunks and AI disabled, concurrency 1, timeout 180 seconds, 1 CPU and 1 GiB.

Execution checklist (completed, including Gemini activation):

1. Verify the archive hash in Cloud Shell and extract into a new release folder.
2. Upload the new snapshot to its digest-named `releases/` object without
   overwriting; record its generation. Upload public source copies privately.
3. Build with `cloudbuild.yaml`; its smoke check expects 39 chunks, no key,
   BM25 health, a working homepage and source-search response under 1 GiB RAM.
4. Create a no-traffic revision using the new image digest, snapshot digest and
   generation, numeric secret version, and `SEARCH_ONLY=false`. Preserve the
   existing CPU, memory, timeout, concurrency and zero-minimum settings.
5. Verify restored snapshot, health modes, actual bilingual answers and sources.
   A candidate URL on this public service is also public; it is not a private
   testing boundary. Publish 100% traffic only after checks pass.
6. Record build/image/revision/object IDs, update README activation status and
   capture the actual public answer. No Git commands are required for deployment.

## Cost and rollback

The existing Gemini key was matched to an AI Studio project displaying Free
tier. Leave its billing unchanged. Quotas are shared with other apps using that
project. Requests may fail when quota is exhausted; do not enable paid billing
to bypass it. Cloud hosting, builds, image storage, network transfer and GCS
continue to have the cost drivers documented in `GOOGLE_CLOUD.md`.

One automatically replicated secret version and ordinary cold-start reads fit
within Secret Manager's account-wide allowance of six active versions and
10,000 reads per month, assuming other account usage leaves enough allowance.
Beyond that allowance, charges apply. Current official references:
https://cloud.google.com/secret-manager/pricing and
https://cloud.google.com/run/docs/configuring/services/secrets.

The app's daily usage ledger remains temporary on Cloud Run. The Free-tier
provider quota, not that ledger, is the boundary against paid Gemini usage.

Rollback to the original search-only release:

```bash
gcloud run services update-traffic korea-visa-rag \
  --project=project-a5074080-2d38-4a35-8b4 --region=us-central1 \
  --to-revisions=korea-visa-rag-00001-pfp=100
```

To disable Gemini while retaining the expanded 39-chunk corpus, use the same
command with `--to-revisions=korea-visa-rag-expanded39=100`. No rebuild, key
disclosure or source migration is needed. Re-enabling the verified AI revision
uses `--to-revisions=korea-visa-rag-gemini39=100`.

Keep its image and original snapshot for rollback. Revisions pin source
snapshots; never attach the expanded snapshot to the old image. Rollback does
not require deleting data, disabling the secret or changing public access.
