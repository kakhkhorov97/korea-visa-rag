# Google Cloud deployment

Prepared 2026-10-25. Sean subsequently approved resource creation, the production
build and private deployment checks. Execution is recorded in
[the release record](CLOUD_RELEASE_2026-10-25.md). Public access and additional
sources were subsequently approved and deployed; see the
[expanded release](EXPANDED_RELEASE_2026-10-26.md). Gemini was subsequently
activated with a pinned Secret Manager version after live checks. Billing
upgrades remain unauthorized. The older Render proposal
remains available as an alternative.

## Inspection and account state

The actual app is FastAPI plus static HTML/CSS/JS, Gemini Developer API,
BM25/Kiwi and local Chroma. The OpenAI references in AGENTS.md are outdated.
There is no hosted application database, separate frontend host, ingestion HTTP
endpoint, streaming response, scheduler, queue or web background worker.
The separate Telegram process uses long polling and is excluded from this web
deployment. No unrelated project's database or hosting should be migrated.

The signed-in Cloud Console showed My First Project, project ID
`project-a5074080-2d38-4a35-8b4`, linked to a Free Trial billing account.
The account showed ₩407,626 of ₩407,626 remaining, 90 days remaining, expiry
January 24, 2027, and current reported cost ₩0. Billing reports can lag.
This confirms the visible account state, not the availability of every API,
quota or IAM permission. Local `gcloud` and Docker are unavailable.
No billing upgrade was performed.

Local verification completed during preparation: 76 tests passed, Python
compilation and dependency checks passed, and the actual 1,551,617-byte public
snapshot was restored into two empty temporary directories. Both restored apps
passed homepage/health checks and returned five official source passages for
the test question without Gemini calls. The checksum is recorded below.
After approval, the production container build, authenticated Storage download
and live API checks passed. Two Cloud Run revisions restored the same snapshot.
The service ran successfully with 1 GiB, but peak Linux memory has not been
measured. See the release record for image/revision identifiers and results.

## Smallest practical architecture

```text
Browser -> HTTPS Cloud Run service -> existing FastAPI + web frontend
                        |
                        +-> existing Gemini Developer API, only if enabled
                        |
                        +-> startup: read private, pinned Storage snapshot
                            -> local chunks + Chroma serving copy

Operator -> local ingestion scripts -> reviewed public sources + existing vectors
         -> versioned release in private Cloud Storage -> new Cloud Run revision
```

Use `us-central1` for Cloud Run, regional Standard Cloud Storage, Artifact
Registry and builds. This favors ongoing free allowances over latency to Korea.
Choose Seoul only after reviewing its different storage/network rates and
accepting the tradeoff. This is a single-region portfolio demo, not an HA system.

One non-root container serves both frontend and API. Keep Gemini and Chroma;
there is no Vertex AI, Cloud SQL, managed vector database, load balancer, VPC
connector, Cloud NAT, scheduler or always-on worker in this proposal.
No frontend build is required. The existing Dockerfile already honors `PORT`
through `scripts/serve.py`, so it needs no replacement.

Proposed Cloud Run settings are 1 vCPU, 1 GiB RAM, concurrency 1, request-based
billing, minimum 0 and service/revision maximum 1, 180-second request timeout,
no CPU boost, one Uvicorn worker. The lightweight Kiwi profile stays enabled.
One GiB gives Chroma and the memory-backed filesystem more headroom than the
earlier 512 MB Render profile; verify Linux peak memory before lowering it.
Cold starts include snapshot download, Chroma restoration and Kiwi loading.
Startup HTTP probing uses `/api/health` with a 240-second failure window.
No external uptime pinger is configured. Scaling to zero is platform-managed,
not an immediate shutdown after each response.

Calls complete inside HTTP requests. Gemini has a 60-second timeout per SDK
call, one attempt, and a hybrid answer can need an embedding call plus a chat
call. There is no SSE/WebSocket timeout to configure. Do not put Telegram
polling or ingestion inside this request-based service. If scheduled ingestion
becomes necessary, design a separately authorized Cloud Run Job with bounded
execution and an uploader identity, then consider Scheduler. Neither is needed now.

## Persistence and public-data boundary

`scripts/export_snapshot.py` exports the reviewed `data/public_raw` corpus and
its existing Chroma vectors as portable JSON. It never embeds. The export
fails if vectors are missing or incomplete, unless `--bm25-only` is explicit.
For this checkout the existing public index is under `data/public_cache/index`.

Cloud Storage holds the durable snapshot and copies of reviewed source files.
The object name contains its SHA-256. Upload uses a create-only precondition,
and each Cloud Run revision pins both the checksum and object generation.
Startup downloads it with the runtime identity and verifies the checksum,
embedding model, all chunks and their exact equality with the image's reviewed
public corpus. Changed sources require a matching image and snapshot.
Any download/validation failure prevents startup; it never silently falls back
to rebuilding embeddings or serving another corpus.

Chroma is reconstructed locally using saved vectors, without a provider call.
That local directory is disposable. The persistent index is the versioned
snapshot in Storage, not Cloud Run's temporary disk. Keep current and rollback
objects; do not run lifecycle deletion against `releases/` or `documents/`.
No SQLite/Chroma files are mounted through Storage FUSE because it lacks the
file-locking behavior these databases need.

The SQLite `usage.sqlite3` stores operational rate counters, not application
records. It remains local and resets on instance replacement. Daily limits
are consequently per instance lifetime within a UTC day, not a durable budget.
Even max-instances 1 can temporarily overlap instances during replacement.
The first deployment explicitly sets `SEARCH_ONLY=true`, so it cannot spend on
Gemini. Before enabling paid AI, approve a durable shared usage reservation
store and provider limits. A confirmed free-tier key can be enabled separately
with quota limitations understood. Do not present the local daily cap as durable.

The public API returns source passages by design. A private bucket alone does
not make indexed material private. Only public statutes may enter this public
snapshot; the importer rejects chunks that differ from the packaged public corpus.
Keep `data/raw`, original HWP files, private documents and `.env` local. If private
documents later need cloud storage, use a separate private bucket with no grant
to this public service, and a separate authenticated retrieval service. No such
upload or migration is part of this proposal.

The runtime account can read only `releases/`, cannot upload/delete documents,
and has no project Editor role. Build identity has no snapshot or secret access.
Ingestion stays an operator-only script; there is no administrative API to expose.
The grounding prompt, citation URLs, abstention instruction, source escaping and
provider-error sanitization remain unchanged. Citations are prompt-based safeguards,
not proof that every generated legal claim is valid.

## Cost and trial implications

Prices below were checked against official documentation on 2026-10-25, in USD
before currency conversion/taxes. Allowances are shared as documented for each
product, not guaranteed separately for this app. Nothing guarantees a zero bill.

| Component | Proposed usage and cost drivers |
|---|---|
| Cloud Run | Request-based monthly allowances include 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests. In Iowa, excess active CPU is $0.000024/vCPU-second, memory $0.0000025/GiB-second, requests $0.40/million. Startup/shutdown and AI waiting time count. |
| Cloud Storage | Eligible US regions include Iowa. Regional Standard allowances include 5 GB-months, 5,000 Class A and 50,000 Class B operations monthly. Each cold start reads object metadata and data. Retained releases, source uploads, soft-deleted objects and build staging occupy storage. |
| Container images | Artifact Registry includes 0.5 GiB-month; excess storage is roughly $0.10/GiB-month. Large Python/Kiwi/Chroma images and retained versions can exceed this. Measure the built image; do not assume it fits the allowance. |
| Builds | Cloud Build lists 2,500 promotional free minutes/month on default-pool e2-standard-2, then $0.006/minute. This configuration selects that machine and a 20-minute timeout. Source staging, logs and transfer are separate. No build triggers are created. |
| Secrets | Optional Secret Manager allowance includes 6 active versions and 10,000 accesses monthly. Extra active versions cost about $0.06/version-month; accesses beyond allowance cost $0.03/10,000. No secret is needed in search-only mode. |
| AI | Existing Gemini Developer API has its own free/paid eligibility and quotas. Do not assume Cloud trial credit covers it. Current Flash-Lite paid text rates are $0.30/million input tokens and $2.50/million output tokens. Query embeddings add usage; initial/restored document vectors are reused. |
| Database/vector | No always-on managed database or vector-service charge. Snapshot bytes/operations and Cloud Run restoration compute are charged under their services. |
| Network/logging | Same-region Storage reads avoid inter-region transfer charges, but operations remain. Cloud Run public egress has a limited North America allowance; traffic to Korean visitors beyond allowances can cost money. Provider traffic and image/source movement can also incur transfer. Logging volume beyond free allowances costs money; avoid logging questions or source text. |

Illustration, not a forecast: 1,000 requests using 10 billed seconds each on
1 vCPU/1 GiB consume about 10,000 CPU-seconds and 10,000 GiB-seconds, before
cold starts, within the listed Run allowances if otherwise unused. A retained
2 GiB image consumes about $0.15/month beyond the registry allowance, before
other costs. With paid AI, 1,000 answers averaging 2,000 input and 500 output
tokens would cost about $1.85 for chat alone. Actual token usage can differ.

At sustained use, a single instance is not a small monthly bill: 30 days of
active 1 vCPU/1 GiB is roughly $63.47 in CPU and memory after the stated free
allowances, before requests, networking and other services. Max scaling bounds
capacity, not spend. Failed/abusive public requests can still consume resources.

Trial credits are temporary and resources stop at trial expiry/exhaustion unless
the account is upgraded. Continuing afterward requires a paid billing account;
monthly free allowances can still apply, with overages billed. Do not upgrade
under this task. Before resources are created, choose a modest alert budget,
for example USD 5/month with 50/90/100% notifications. Alerts do not enforce a
cap in this proposal. Check gross service costs as well as credits so the trial
does not hide the post-trial run rate. Review before January 24, 2027.

## Reproducible deployment commands

Run from this repository. These document the first-deployment process. The
approved execution used Cloud Shell; do not blindly rerun resource creation.
Install official Google Cloud CLI locally or use Cloud Shell. Cloud
Shell does not have these uncommitted changes; transfer only the reviewed files
or commit/push them manually and fetch the exact commit there. Do not upload the
entire local directory through a browser. Never paste secrets into chat.

First, read-only checks:

```bash
export PROJECT_ID=project-a5074080-2d38-4a35-8b4
export REGION=us-central1
export SERVICE=korea-visa-rag
export BUCKET="${PROJECT_ID}-visa-data"
export REPOSITORY=visa
export RUNTIME_SA="visa-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export BUILD_SA="visa-builder@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud auth list
gcloud projects describe "$PROJECT_ID"
gcloud billing projects describe "$PROJECT_ID"
gcloud services list --enabled --project="$PROJECT_ID"
gcloud run services list --project="$PROJECT_ID" --region="$REGION"
gcloud storage buckets list --project="$PROJECT_ID"
```

Stop if the project/billing account differs from the approved target. A deployer
needs service creation/IAM/API permissions, Cloud Build submission, repository
upload and service-account `actAs` rights. Grant narrowly to the human deployer
if missing; do not grant Owner/Editor to runtime or build identities.
If a service or bucket with these names already exists, inspect it before any
mutation. These first-deployment commands must not overwrite another workload.

After explicit resource/cost approval only, provision once:

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com storage.googleapis.com iam.googleapis.com \
  --project="$PROJECT_ID"
gcloud iam service-accounts create visa-runtime --project="$PROJECT_ID"
gcloud iam service-accounts create visa-builder --project="$PROJECT_ID"
gcloud storage buckets create "gs://${BUCKET}" --project="$PROJECT_ID" \
  --location="$REGION" --default-storage-class=STANDARD \
  --uniform-bucket-level-access --public-access-prevention
gcloud storage buckets update "gs://${BUCKET}" \
  --lifecycle-file=deploy/storage-lifecycle.json
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" --role=roles/storage.objectViewer \
  --condition="expression=resource.name.startsWith('projects/_/buckets/${BUCKET}/objects/releases/'),title=public_snapshot_reader"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/storage.objectViewer \
  --condition="expression=resource.name.startsWith('projects/_/buckets/${BUCKET}/objects/build/source/'),title=build_source_reader"
gcloud artifacts repositories create "$REPOSITORY" --project="$PROJECT_ID" \
  --location="$REGION" --repository-format=docker
gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" \
  --project="$PROJECT_ID" --location="$REGION" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/artifactregistry.writer
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/logging.logWriter
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${BUILD_SA}" --role=roles/serviceusage.serviceUsageConsumer
```

The bucket lifecycle deletes only build staging objects older than 14 days.
Default soft-delete retention can keep deleted bytes billable for longer.
No release, source-document or production-data deletion is configured.
For registry cleanup, first inspect image sizes and retain the current and
rollback digests; preview a cleanup policy before applying any deletion.
The same-project Cloud Run service agent pulls images using its managed role;
the runtime account itself does not need registry write/read grants.

Prepare the local release without provider calls:

```bash
.venv/bin/python scripts/export_snapshot.py --index-root data/public_cache/index
export SNAPSHOT_SHA=a7d9cb8bdf3e60dc775859f65dba3ce9630d50ff28923fa4829f703257b4960a
export SNAPSHOT_URI="gs://${BUCKET}/releases/${SNAPSHOT_SHA}.json"
shasum -a 256 "data/releases/${SNAPSHOT_SHA}.json"
```

Use the digest printed by your export if sources/model/vectors have changed.
The shown digest is the actual local export from this preparation. If no matching
index is present, copy the reviewed export from this machine or explicitly choose
`--bm25-only`. Do not trigger embedding ingestion merely to deploy.

After upload approval:

```bash
gcloud storage cp "data/releases/${SNAPSHOT_SHA}.json" "$SNAPSHOT_URI" \
  --if-generation-match=0
gcloud storage cp data/public_raw/*.txt "gs://${BUCKET}/documents/${SNAPSHOT_SHA}/" \
  --if-generation-match=0
export SNAPSHOT_GENERATION="$(gcloud storage objects describe "$SNAPSHOT_URI" --format='value(generation)')"
```

If an object already exists, verify its generation and checksum; do not overwrite
it. Source copies remain private and the runtime has no read permission for their
prefix. No private originals are uploaded.

Build after build-cost approval. `.gcloudignore` separately protects the uploaded
build context; Docker's ignore file alone would not prevent source upload.

```bash
gcloud meta list-files-for-upload
export RELEASE="$(date -u +%Y%m%d%H%M%S)"
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/app:${RELEASE}"
gcloud builds submit . --project="$PROJECT_ID" --region="$REGION" \
  --config=cloudbuild.yaml --substitutions="_IMAGE=${IMAGE}" \
  --service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA}" \
  --gcs-source-staging-dir="gs://${BUCKET}/build/source" \
  --ignore-file=.gcloudignore
export IMAGE_DIGEST="$(gcloud artifacts docker images describe "$IMAGE" --project="$PROJECT_ID" --format='value(image_summary.digest)')"
export PINNED_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/app@${IMAGE_DIGEST}"
```

The production build performs a container secret-exclusion, health, homepage and
cited-answer smoke test before pushing. Snapshot round-trip tests run locally
with pytest; the authenticated cloud download must also pass the live check.
The approved production build is linked in the release record. If uploads contain anything
outside the allowlist, stop before submitting.

Create the initial service privately after deployment approval:

```bash
gcloud run deploy "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --image="$PINNED_IMAGE" --service-account="$RUNTIME_SA" \
  --execution-environment=gen2 --port=8080 --cpu=1 --memory=1Gi \
  --cpu-throttling --no-cpu-boost --concurrency=1 --timeout=180 \
  --min=0 --max=1 --min-instances=0 --max-instances=1 \
  --ingress=all --no-allow-unauthenticated \
  --startup-probe=httpGet.path=/api/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=5,failureThreshold=24 \
  --set-env-vars="SEARCH_ONLY=true,KIWI_LIGHTWEIGHT=true,API_REQUESTS_PER_MINUTE=20,API_DAILY_AI_REQUESTS=100,API_MAX_CONCURRENT_AI=1,VISARAG_SNAPSHOT_URI=${SNAPSHOT_URI},VISARAG_SNAPSHOT_GENERATION=${SNAPSHOT_GENERATION},VISARAG_SNAPSHOT_SHA256=${SNAPSHOT_SHA}"
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION"
gcloud run services proxy "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --port=8081
```

Keep the proxy running and test from another terminal:

```bash
curl --fail http://127.0.0.1:8081/api/health
curl --fail http://127.0.0.1:8081/
curl --fail -H 'Content-Type: application/json' \
  -d '{"question":"D-10 구직 체류자격"}' http://127.0.0.1:8081/api/ask
curl --fail -H 'Content-Type: application/json' \
  -d '{"question":"Can I work on a D-2 visa?"}' http://127.0.0.1:8081/api/ask
```

Expect 22 chunks, `llm: false`, `modes: ["bm25"]`, source passages and official
URLs. English keyword recall is limited in search-only mode. This is not a test
of bilingual AI answer quality. Inspect startup logs for the pinned digest and
`vectors: True`. An unauthenticated request to the service URL must be denied.

## Optional AI activation, separate approval

Keep the existing Gemini Developer API, not Vertex AI. Verify the key's project,
free-tier eligibility, model access and billing state in AI Studio. A Cloud
trial account does not verify the API key's pricing tier. Do not attach paid AI
billing as part of this task. Free-tier model requests can be used for Google's
product improvement; keep private material out of this public assistant.

After secret/AI approval, create a Secret Manager secret and enter its value
directly through the Google Cloud console's secret-version form. Never put the
key into a shell command, build argument, YAML file, frontend variable or chat.
Enable `secretmanager.googleapis.com`, then grant only this secret to runtime:

```bash
gcloud secrets add-iam-policy-binding visa-gemini-key --project="$PROJECT_ID" \
  --member="serviceAccount:${RUNTIME_SA}" --role=roles/secretmanager.secretAccessor
gcloud run services update "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --update-env-vars=SEARCH_ONLY=false,GEMINI_CHAT_MODEL=gemini-3.5-flash-lite,GEMINI_EMBED_MODEL=gemini-embedding-001 \
  --update-secrets=GEMINI_API_KEY=visa-gemini-key:1
```

Replace `1` with the reviewed numeric secret version. Avoid `latest` so rollback
is reproducible. Only the runtime can access it; the builder cannot. With the
vector snapshot, health must now advertise hybrid/BM25/vector. Run a separately
approved real Gemini query and confirm citations, English/Korean answers,
out-of-scope behavior and safe quota failures. No document embeddings should
be requested on cold start. If the index/model changes, produce a new matching
snapshot, never a writable shared live Chroma mount.

## Publication checklist and rollback

- [ ] Approve project, Iowa location, resources, cost drivers and alert budget.
- [ ] Manually review/commit the changes if desired. No staging or Git mutation was done here.
- [ ] Pass pytest and the production container build; record build ID, image digest,
  snapshot digest/generation, revision and optional secret version in a release record.
- [ ] Verify private bucket and prefix-scoped runtime access; no public bucket grants.
- [ ] Deploy privately and verify health, sources, cold-start memory/time and rate errors.
- [ ] Test persistence with two new revisions or a genuine scale-down/scale-up: both
  must restore the same digest and vectors with no document embedding calls.
- [ ] Confirm a deliberately wrong digest/generation fails a private test revision.
- [ ] Confirm no ingestion route or private material is reachable via public search.
- [ ] For AI, verify provider tier and test cited answers separately before publication.
- [ ] Approve public exposure of the existing web/API service, then run the IAM command below.
- [ ] Test the public URL, update README to reflect actual deployment, review gross costs.
- [ ] Review retained images, staging objects and billing before the trial expires.

Publish only after explicit public-access approval:

```bash
gcloud run services add-iam-policy-binding "$SERVICE" --project="$PROJECT_ID" \
  --region="$REGION" --member=allUsers --role=roles/run.invoker
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --format='value(status.url)'
```

Do not use `--no-invoker-iam-check` as a workaround for an IAM policy denial.
All existing API routes and API docs become public along with the frontend;
there is no administrative endpoint. The bucket and Secret Manager stay private.
The app ignores forwarded IP headers, so multiple users behind Cloud Run's proxy
may share a rate bucket. This conservative behavior is unchanged.

Before an update, record the known-good revision:

```bash
gcloud run revisions list --service="$SERVICE" --project="$PROJECT_ID" --region="$REGION"
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --format='yaml(status.traffic,status.latestReadyRevisionName)'
```

For later releases, deploy with `--no-traffic --tag=candidate`, test the tagged
URL, then explicitly shift traffic. Retain at least the known-good image,
snapshot object/generation and secret version. Roll back code and index together:

```bash
export GOOD_REVISION=REPLACE_WITH_RECORDED_REVISION
gcloud run services update-traffic "$SERVICE" --project="$PROJECT_ID" \
  --region="$REGION" --to-revisions="${GOOD_REVISION}=100"
```

Old snapshots and secrets must still exist for a cold start of the old revision.
Traffic rollback does not restore IAM policy or undo external data writes.
To immediately restrict public access, remove the `allUsers` invoker binding.
To disable AI, update `SEARCH_ONLY=true`; do not destroy a key needed for rollback.
To stop compute entirely, delete the service only after authorization, retaining
release records and required artifacts. Storage/image/secret charges can remain
after the service stops. Resource deletion is not part of this preparation.

## Official references

- [Cloud Run pricing](https://cloud.google.com/run/pricing)
- [Trial and ongoing free allowances](https://docs.cloud.google.com/free/docs/free-cloud-features)
- [Cloud Storage pricing](https://cloud.google.com/storage/pricing)
- [Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing)
- [Cloud Build pricing](https://cloud.google.com/build/pricing)
- [Secret Manager pricing](https://cloud.google.com/secret-manager/pricing)
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Cloud Run container contract and temporary filesystem](https://docs.cloud.google.com/run/docs/container-contract)
- [Storage FUSE limitations](https://docs.cloud.google.com/storage/docs/cloud-storage-fuse/overview)
- [Cloud Run deployment flags](https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy)
- [Storage generation preconditions](https://docs.cloud.google.com/storage/docs/request-preconditions)
- [Storage IAM roles](https://docs.cloud.google.com/storage/docs/access-control/iam-roles)
- [Cloud Run secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets)
- [Budgets](https://docs.cloud.google.com/billing/docs/how-to/budgets)
- [Traffic rollback](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
