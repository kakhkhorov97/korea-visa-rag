# Public beta: prepared deployment, awaiting cloud approval

Prepared locally on 2026-10-26. These commands have **not** been run against
the cloud project for this beta. The current public service still runs the
39-chunk `korea-visa-rag-language` revision at
https://korea-visa-rag-jwq77bpivq-uc.a.run.app/.

## What changes

The existing Cloud Run service, Gemini Developer API Free-tier key in Secret
Manager, private regional Standard bucket, Artifact Registry repository and
builder/runtime accounts remain in place. The web frontend stays in the
FastAPI container. No new database, queue, scheduler, Telegram worker, VPC
connector or data migration is needed. A new immutable private snapshot stores
the 44 reviewed public statute chunks and 44 existing vectors; Cloud Run
restores Chroma locally at startup without calling the embedding provider.
The previous 39-chunk snapshot and revision are retained for rollback.

The beta starts in source-only keyword search. An adult visitor in South Korea
may explicitly enable AI answers after reading the privacy notice. This is
self-attestation, not age or location verification; review Gemini terms before
opening AI to other audiences. Questions matching common identity-number,
passport, phone or email patterns are rejected before retrieval, but this
cannot catch all personal data. Do not enter personal information. Generated
claims need an exact source quotation; the application adds citations. Invalid
answers and provider failures show original passages with a notice. Quotation
matching cannot establish legal accuracy. The 36-question review needs a
separate qualified human review before making such a claim.

The new usage ledger is one private Cloud Storage JSON object per UTC day.
Generation preconditions reserve global slots across instance replacements:
20 requests/minute, 500 requests/day, 100 AI requests/day and one local
simultaneous AI call. Failed AI calls count. No question, answer or visitor IP is
written to the ledger. The runtime identity gets read/create/delete only under
`usage/public-beta/` through a conditional bucket binding. If the counter is
unavailable, requests fail closed. The cap is a request limit, not an absolute
bill cap, a per-person limit or a general bot defense. An attacker can deny
other visitors by exhausting the shared limit. Cloud Run traffic and rejected
requests can still incur charges.

The deployment retains 1 vCPU, 1 GiB, concurrency 1, a 180-second request
timeout, request-based CPU, zero minimum instances, maximum one instance and
one Uvicorn worker. Cold starts download and check the snapshot and load Kiwi
and Chroma; a five-minute uptime check may reduce time at zero instances.
Ingestion remains a manual operator job outside the service. There is no
streaming, scheduled ingestion or request-independent background worker.
Private HiKorea files and administrative ingestion scripts stay out of the
public image. The API remains public for general questions; the private
bucket and Secret Manager stay private.

## Account and cost checkpoint

Read-only checks found project `project-a5074080-2d38-4a35-8b4`, a linked and
enabled billing account, the live service, the existing bucket and identities.
An earlier dashboard showed Free Trial credit of about ₩407,626 with expiry on
January 24, 2027. The billing link alone does not confirm the latest credit
balance or a billing upgrade. Recheck the dashboard before deployment.
The project also contains unrelated CargoCheck resources; these commands do
not alter them or create a project-wide spend cap.

Likely incremental charges are small at modest traffic, but no lasting zero-cost
promise is possible. The following are USD list-price illustrations before
taxes, exchange rates and shared free allowances:

| Driver | Proposed usage and implication |
|---|---|
| Cloud Run | Existing 1 vCPU/1 GiB, max one, min zero. Active requests, AI waiting time and cold starts consume CPU/memory allowances; public requests and Korean egress also count. The existing monthly allowances are shared across the billing account. A busy single instance can cost much more than an idle demo. |
| Storage | The new snapshot is about 3.1 MB, plus 44 small source files only if copied. At 500 accepted requests/day, roughly 15,000 ledger writes and 30,000 reads/month are about **$0.087 before free operation allowances**, plus storage, retries and rejected traffic. The eligible regional free allowances are 5 GB-month, 5,000 Class A and 50,000 Class B operations shared with other usage. Soft-deleted objects may remain billable seven more days. |
| Build and image | One Cloud Build execution and one more Artifact Registry image/layer set; default-pool promotional minutes and the registry's 0.5 GiB free storage allowance are shared. The existing Python image may already exceed the registry allowance. Retain old digests for rollback. |
| AI | The current Gemini key is reportedly Free tier, separate from Google Cloud trial credit. 100 daily AI reservations bound requests, not tokens or a provider bill. No automatic document re-embedding occurs; query embeddings and chat use provider quota. Do not attach paid AI billing without separate approval. |
| Monitoring | A 5-minute health check from the US is about 25,920 checks/month if three checkers run, below Monitoring's 1 million project-wide free uptime executions if unused elsewhere. The two dashboard-only alert policies have no email channel. Metric-based policy pricing is scheduled no sooner than September 2027; check then. Health requests can wake Cloud Run. |
| Other | Secret Manager reads, Cloud Logging, Storage operations, outbound transfer, and build source staging retain their normal rates and allowances. There is no managed database or separate vector-service fee. |

Trial credit can cover eligible Google Cloud charges until exhausted or expired;
continuing beyond it requires checking the actual billing state and accepting
any overage. Free product allowances are subject to current terms. Review gross
costs, not only the credit-adjusted bill. No billing upgrade is part of this
release. Official references: [Cloud Run pricing](https://cloud.google.com/run/pricing),
[Storage pricing](https://cloud.google.com/storage/pricing),
[Cloud Build pricing](https://cloud.google.com/build/pricing),
[Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing),
[Monitoring pricing](https://cloud.google.com/products/observability/pricing),
[Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing),
[Gemini terms](https://ai.google.dev/gemini-api/terms), and
[Storage preconditions](https://cloud.google.com/storage/docs/request-preconditions).

## Local release evidence

Run tests before packaging. This is the current local snapshot, exported without
another embedding call:

```
SHA-256: dde1fed36a8d42e06a10b29a84b32054a3dfbfbd0c16912c2c812f6bc80cb477
File: data/releases/<SHA-256>.json
Size: 3,103,545 bytes
Corpus: 44 public chunks, 44 saved gemini-embedding-001 vectors
```

The saved file was restored into a fresh local directory on 2026-10-26;
checksum and corpus checks passed, all 44 chunks returned, and the Chroma
index existed with `vectors: True`. No embedding call was made. The cloud
download, IAM binding and new revision remain unverified until approval.

`scripts/package_beta.py` builds a narrow release archive for Cloud Shell.
It includes only the application, public statute excerpts, font license and
deployment manifests; `.env`, private HiKorea files, original documents,
local indexes and Git metadata are excluded. Check its printed SHA before
uploading. Upload of this archive and snapshot requires the final cloud
approval below.

```bash
.venv/bin/python -m pytest -q
node --test tests/test_web.cjs
python3 scripts/package_beta.py
shasum -a 256 /tmp/visa-beta-release-20261026.zip
```

## Reproducible cloud procedure, only after approval

In Cloud Shell, create a fresh `~/visa-beta-release-20261026` directory and
upload the reviewed archive there with Cloud Shell's file upload control.
Check its SHA against the local printout, unzip, and work inside that directory.
Do not pull an arbitrary Git branch: local changes may still be uncommitted.
Never paste the Gemini key into a command, file, browser URL or chat. The existing
`visa-gemini-key:1` reference stays on the service.

```bash
export PROJECT_ID=project-a5074080-2d38-4a35-8b4
export REGION=us-central1
export SERVICE=korea-visa-rag
export BUCKET="${PROJECT_ID}-visa-data"
export RUNTIME_SA="visa-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export BUILD_SA="visa-builder@${PROJECT_ID}.iam.gserviceaccount.com"
export SNAPSHOT_SHA=dde1fed36a8d42e06a10b29a84b32054a3dfbfbd0c16912c2c812f6bc80cb477
export SNAPSHOT_URI="gs://${BUCKET}/releases/${SNAPSHOT_SHA}.json"
gcloud config get-value project
gcloud billing projects describe "$PROJECT_ID"
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format=json > before-beta-service.json
gcloud storage buckets describe "gs://${BUCKET}" --format=json > before-beta-bucket.json
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(status.traffic[0].revisionName)'
```

Stop if the project, billing, current revision, bucket lifecycle, secret
reference, identity or 39-chunk public health differs from this plan. Inspect
the archive before changing IAM. Upload the 44-chunk snapshot separately from
this machine to Cloud Shell and check its SHA. The Cloud Shell uploader must
have the normal object-creator permission on the existing private bucket.

```bash
shasum -a 256 "${SNAPSHOT_SHA}.json"
gcloud storage cp "${SNAPSHOT_SHA}.json" "$SNAPSHOT_URI" --if-generation-match=0
export SNAPSHOT_GENERATION="$(gcloud storage objects describe "$SNAPSHOT_URI" --format='value(generation)')"
test -n "$SNAPSHOT_GENERATION"
gcloud iam roles create visaBetaUsageWriter --project="$PROJECT_ID" --file=deploy/beta-usage-role.yaml
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${RUNTIME_SA}" \
  --role="projects/${PROJECT_ID}/roles/visaBetaUsageWriter" \
  --condition="expression=resource.name.startsWith('projects/_/buckets/${BUCKET}/objects/usage/public-beta/'),title=visa_beta_usage_only"
gcloud storage buckets update "gs://${BUCKET}" --lifecycle-file=deploy/beta-lifecycle.json
```

If the snapshot already exists, verify its digest and generation; never
overwrite it. The lifecycle file retains the existing 14-day `build/source/`
rule and adds 30-day deletion only to old `usage/public-beta/` counter objects.
It does not target `releases/`, source documents or unrelated objects. IAM
create/delete rights are required for conditional replacement of a ledger
object; the binding's resource prefix is the important restriction. Test it
with the candidate revision and inspect its effective IAM policy before traffic.

Build from the extracted archive using the existing builder identity. Confirm
`gcloud meta list-files-for-upload` contains only public application files.
The build tests a 44-chunk keyless container before pushing a new image.

```bash
gcloud meta list-files-for-upload
export IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/visa/app:20261026-beta44"
gcloud builds submit . --project="$PROJECT_ID" --region="$REGION" \
  --config=cloudbuild.beta.yaml --substitutions="_IMAGE=${IMAGE}" \
  --service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA}" \
  --gcs-source-staging-dir="gs://${BUCKET}/build/source" \
  --ignore-file=.gcloudignore
export IMAGE_DIGEST="$(gcloud artifacts docker images describe "$IMAGE" --project="$PROJECT_ID" --format='value(image_summary.digest)')"
test -n "$IMAGE_DIGEST"
export PINNED_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/visa/app@${IMAGE_DIGEST}"
```

Create a **zero-traffic** candidate that retains the current secret mapping,
public service URL and existing runtime identity. `--update-env-vars` preserves
other existing variables. Set the new snapshot generation returned above; do
not guess it. The `beta` tag URL is publicly reachable once created, so do not
share it until smoke checks pass.

```bash
gcloud run deploy "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --image="$PINNED_IMAGE" --service-account="$RUNTIME_SA" \
  --execution-environment=gen2 --cpu=1 --memory=1Gi --cpu-throttling --no-cpu-boost \
  --concurrency=1 --timeout=180 --min=0 --max=1 --min-instances=0 --max-instances=1 \
  --startup-probe=httpGet.path=/api/health,httpGet.port=8080,periodSeconds=10,timeoutSeconds=5,failureThreshold=24 \
  --update-env-vars="VISARAG_PUBLIC_BETA=true,VISARAG_USAGE_URI=gs://${BUCKET}/usage/public-beta,API_REQUESTS_PER_MINUTE=20,API_DAILY_REQUESTS=500,API_DAILY_AI_REQUESTS=100,API_MAX_CONCURRENT_AI=1,VISARAG_SNAPSHOT_URI=${SNAPSHOT_URI},VISARAG_SNAPSHOT_GENERATION=${SNAPSHOT_GENERATION},VISARAG_SNAPSHOT_SHA256=${SNAPSHOT_SHA}" \
  --no-traffic --tag=beta
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format=json > candidate-service.json
export CANDIDATE_URL="$(python3 -c 'import json; d=json.load(open("candidate-service.json")); print(next(t["url"] for t in d["status"]["traffic"] if t.get("tag")=="beta"))')"
export CANDIDATE_REVISION="$(python3 -c 'import json; d=json.load(open("candidate-service.json")); print(next(t["revisionName"] for t in d["status"]["traffic"] if t.get("tag")=="beta"))')"
test -n "$CANDIDATE_URL"
test -n "$CANDIDATE_REVISION"
```

Check the candidate before shifting traffic. Expect `chunks: 44`, `llm: true`,
three search modes, `ai_ack_required: true`, `shared_limits: true`, a 403 for
AI without acknowledgment, and a source-only answer with no Gemini request.
Check `/privacy` and a private-identifier rejection (422). A single consented
AI sample verifies citations; it spends one free-provider request and should
return an answer or a clearly labeled source fallback. Inspect startup logs for
the exact snapshot SHA and `vectors: True`; verify no exception is leaked and
that the live 39-chunk URL still serves its old revision.

```bash
curl --fail "$CANDIDATE_URL/api/health"
curl --fail "$CANDIDATE_URL/privacy"
curl --fail -H 'Content-Type: application/json' \
  -d '{"question":"D-10 체류기간","source_only":true}' "$CANDIDATE_URL/api/ask"
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Content-Type: application/json' \
  -d '{"question":"D-10 체류기간"}' "$CANDIDATE_URL/api/ask"
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Content-Type: application/json' \
  -d '{"question":"What about test@example.com?","source_only":true}' "$CANDIDATE_URL/api/ask"
```

After the candidate passes, create a five-minute HTTPS `/api/health` uptime
check and two alert policies with **no notification channels**. These will
appear in Cloud Monitoring dashboards; they will not send mail. The check
causes billable/allowance-counted requests and may wake the service. Use the
existing public hostname in `deploy/beta-uptime.json`. Create each only if no
same-named check or policy already exists. The uptime policy needs the actual
check ID substituted for its placeholder.

```bash
gcloud monitoring uptime list-configs --project="$PROJECT_ID"
gcloud monitoring policies list --project="$PROJECT_ID"
gcloud monitoring uptime create 'Visa beta health' \
  --project="$PROJECT_ID" --resource-type=uptime-url \
  --resource-labels="project_id=${PROJECT_ID},host=korea-visa-rag-jwq77bpivq-uc.a.run.app" \
  --protocol=https --port=443 --path=/api/health --period=5 --timeout=30 \
  --regions=usa-iowa,usa-oregon,usa-virginia --validate-ssl=true
gcloud monitoring policies create --project="$PROJECT_ID" \
  --policy-from-file=deploy/beta-server-errors.json
export UPTIME_NAME="$(gcloud monitoring uptime list-configs --project="$PROJECT_ID" --format=json | python3 -c 'import json,sys; rows=json.load(sys.stdin); matches=[r["name"] for r in rows if r.get("displayName")=="Visa beta health"]; assert len(matches)==1, matches; print(matches[0])')"
export CHECK_ID="${UPTIME_NAME##*/}"
python3 -c 'import pathlib,sys; src=pathlib.Path("deploy/beta-uptime-alert.json").read_text(); assert src.count("REPLACE_WITH_CREATED_CHECK_ID")==1; pathlib.Path("/tmp/visa-beta-uptime-alert.json").write_text(src.replace("REPLACE_WITH_CREATED_CHECK_ID",sys.argv[1]))' "$CHECK_ID"
gcloud monitoring policies create --project="$PROJECT_ID" \
  --policy-from-file=/tmp/visa-beta-uptime-alert.json
```

The commands place the created uptime check ID in a temporary copy of the
reviewed alert file. Verify both policies list zero notification channels.
Because dashboard-only alerts require someone to look, inspect Monitoring and
Billing manually after launch and at least weekly afterward.

Finally, route traffic to the new revision identified in
`candidate-service.json`. Record the previous revision from
`before-beta-service.json` before running this. Check health, the homepage,
source search and one consented AI query at the public URL. If any check fails,
route back immediately. Keep the old image and snapshot.

```bash
gcloud run services update-traffic "$SERVICE" --project="$PROJECT_ID" \
  --region="$REGION" --to-revisions="${CANDIDATE_REVISION}=100"
curl --fail https://korea-visa-rag-jwq77bpivq-uc.a.run.app/api/health
```

## Rollback and maintenance

The current known-good rollback revision is `korea-visa-rag-language`, pinned
to the original 39-chunk snapshot. Route 100% back and verify its health and
source search. Do not delete the beta ledger, snapshot or image during an
incident; they aid diagnosis and rollback. If the runtime loses write access
to `usage/public-beta/`, the beta intentionally stops serving questions.

```bash
gcloud run services update-traffic korea-visa-rag \
  --project=project-a5074080-2d38-4a35-8b4 --region=us-central1 \
  --to-revisions=korea-visa-rag-language=100
curl --fail https://korea-visa-rag-jwq77bpivq-uc.a.run.app/api/health
```

For subsequent source updates, fetch and review official law text, rebuild the
matching public index as an explicit operator task, export a new snapshot,
verify source URLs and hashes, run the labeled review and tests, then repeat
the image/snapshot release process. Never rebuild embeddings on Cloud Run
startup. Keep private guidance out of the public package unless its reuse and
access restrictions have been resolved.
