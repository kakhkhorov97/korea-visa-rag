# GitHub Actions release to Cloud Run

The workflow in `.github/workflows/deploy-cloud-run.yml` is **manual**. A push
to `develop` or `main` runs the existing tests; it does not deploy. After the
reviewed change is on `main`, run **Actions → Deploy Cloud Run beta → Run
workflow** on `main`. One run tests, builds with the existing Cloud Build
builder, deploys a zero-traffic candidate, checks the candidate, then moves
100% of the existing service's traffic to it. If the final public check fails,
it attempts to restore the previously live revision.

The workflow deliberately supports only the current 44-chunk public corpus and
the pinned snapshot recorded in `docs/PUBLIC_BETA_DEPLOYMENT.md`. Source,
embedding-model or snapshot changes need a separately reviewed release and an
updated gate. The Gemini key stays in Cloud Run's Secret Manager mapping; the
workflow does not receive that key. GitHub does not store a Google service
account key.

The build uses Cloud Build's default e2-standard-2 worker. Do not set
`options.machineType` to that default in `cloudbuild.beta.yaml`; the build
submission rejects it as an unused option.

The AI smoke test asks for the D-10 maximum stay because the reviewed public
source states that limit and its exception. The candidate must return an
English AI answer with verified citations. A broad D-10 category question
returned the app's safe source-only fallback during the first live run, so it
is not used as the release gate. That fallback remains the right behavior when
the app cannot verify an AI answer.

## One-time setup

The current Google Cloud project has these grants and the GitHub `production`
environment in place as of October 27, 2026. The commands below are a
reproducible template for checking or rebuilding the setup, not steps to rerun
for every release. Check the current service, billing, IAM policies and project
ID before applying any command. The identity provider accepts only this
repository's `main` branch. Do not create a second project, bucket, registry
or Gemini key for routine releases.

```bash
export PROJECT_ID=YOUR_PROJECT_ID
export PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
export REPO=kakhkhorov97/korea-visa-rag
export DEPLOY_SA="visa-github-deployer@${PROJECT_ID}.iam.gserviceaccount.com"
export RUNTIME_SA="visa-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
export BUILD_SA="visa-builder@${PROJECT_ID}.iam.gserviceaccount.com"
export BUCKET="${PROJECT_ID}-visa-data"

gcloud iam service-accounts create visa-github-deployer --project="$PROJECT_ID"
gcloud iam workload-identity-pools create visa-github --project="$PROJECT_ID" \
  --location=global --display-name='Visa GitHub releases'
gcloud iam workload-identity-pools providers create-oidc main \
  --project="$PROJECT_ID" --location=global --workload-identity-pool=visa-github \
  --issuer-uri='https://token.actions.githubusercontent.com' \
  --attribute-mapping='google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner,attribute.ref=assertion.ref' \
  --attribute-condition="assertion.repository_owner=='kakhkhorov97' && assertion.repository=='${REPO}' && assertion.ref=='refs/heads/main'"
export POOL="projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/visa-github"
gcloud iam service-accounts add-iam-policy-binding "$DEPLOY_SA" --project="$PROJECT_ID" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/${POOL}/attribute.repository/${REPO}"
```

Grant the deployer build submission, project service usage, image inspection,
and update access to the **existing** service, plus permission to act as the two
existing service accounts. The Cloud Build permission can submit arbitrary
builds and the service-usage role can consume project quota, so keep the
provider restricted to the reviewed `main` branch and audit who may push or
merge to it. The source-upload grant is limited to the build staging prefix;
bucket viewing exposes metadata only, not private document contents.

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/cloudbuild.builds.editor
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/serviceusage.serviceUsageConsumer
gcloud run services add-iam-policy-binding korea-visa-rag \
  --project="$PROJECT_ID" --region=us-central1 \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/run.developer
gcloud iam service-accounts add-iam-policy-binding "$RUNTIME_SA" \
  --project="$PROJECT_ID" --member="serviceAccount:${DEPLOY_SA}" \
  --role=roles/iam.serviceAccountUser
gcloud iam service-accounts add-iam-policy-binding "$BUILD_SA" \
  --project="$PROJECT_ID" --member="serviceAccount:${DEPLOY_SA}" \
  --role=roles/iam.serviceAccountUser
gcloud artifacts repositories add-iam-policy-binding visa \
  --project="$PROJECT_ID" --location=us-central1 \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/artifactregistry.reader
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/storage.objectCreator \
  --condition="expression=resource.name.startsWith('projects/_/buckets/${BUCKET}/objects/build/source/'),title=github_build_source_only"
gcloud storage buckets add-iam-policy-binding "gs://${BUCKET}" \
  --member="serviceAccount:${DEPLOY_SA}" --role=roles/storage.bucketViewer
```

In GitHub, create a `production` environment and restrict it to `main`; add a
required reviewer if your repository settings allow it. Set these **repository
variables**, not secrets, under Settings → Secrets and variables → Actions:

- `GCP_PROJECT_ID`: the existing project ID.
- `GCP_WIF_PROVIDER`: `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/visa-github/providers/main`.
- `GCP_DEPLOY_SA`: `visa-github-deployer@PROJECT_ID.iam.gserviceaccount.com`.

Do not add `GEMINI_API_KEY`, a service account JSON key or document files to
GitHub. Workload Identity Federation issues short-lived credentials to the
workflow. The existing runtime service account reads the private snapshot and
Secret Manager at startup, just as the current release does.

## Release and rollback

Review the `develop` changes, merge them to `main` yourself, and confirm the
push-triggered test and container workflows are green. Start the manual deploy
action on `main`. Check the action log for the image digest, candidate checks,
new revision and public URL. Then open the app and test source search and one
consented, general English AI question. The action does not upload new source
documents or rebuild embeddings. If a source file has changed, stop and use
the snapshot release procedure in `PUBLIC_BETA_DEPLOYMENT.md` first.

For rollback, use Cloud Run → `korea-visa-rag` → Revisions → Manage traffic to
send 100% back to the recorded previous revision. Keep that revision's image,
snapshot and Secret Manager version until the new one is verified. The action's
automatic rollback only covers failures detected in its final public health
and favicon checks; it cannot prove legal accuracy or catch later outages.

Each release consumes GitHub runner time, Cloud Build minutes, source staging
operations, Artifact Registry image storage and candidate/public Cloud Run
requests. The single AI smoke test uses one Gemini request. The existing
private snapshot is reused, so this code-only release does not create a new
index object. Free allowances and trial credit may cover usage, but are not a
permanent zero-cost guarantee. Review billing before each run.

Official references: [GitHub Actions authentication with Workload Identity
Federation](https://github.com/google-github-actions/auth), [Google Cloud
federation for deployment pipelines](https://docs.cloud.google.com/iam/docs/workload-identity-federation-with-deployment-pipelines),
[Cloud Run traffic rollouts](https://docs.cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration),
[Cloud Build pricing](https://cloud.google.com/build/pricing),
[Artifact Registry pricing](https://cloud.google.com/artifact-registry/pricing),
and [Cloud Run pricing](https://cloud.google.com/run/pricing).
