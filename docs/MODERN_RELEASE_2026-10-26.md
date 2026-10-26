# Modern web release

## Scope and validation

The approved generated image is `docs/design/modern-demo-v1.png`. The web app
now uses an ink-blue search sidebar, a white conversation area and a sage
original-source panel. It remains plain HTML, CSS and JavaScript on FastAPI.
The backend, model configuration, public corpus and persistent snapshot are
unchanged. No Git staging, commit or push is part of this release.

- Python tests: 77 passed with real libraries.
- Node browser-rendering tests: 5 passed. They check escaping, citation ranges,
  URL protocols, mixed prose/list formatting and mobile reply navigation.
- Actual desktop and 390px phone checks covered questions, citation navigation,
  original passages, the menu and a second submission from the evidence area.
  Both loading and the completed second answer started at 84px, below the header;
  document width equalled viewport width at 390px.
- The independent full review requested two functional corrections. Its focused
  follow-up marked both resolved. It accepted the overall composition, with
  denser source content than the mockup. It did not certify exact visual fidelity.
- The automated image comparison scores approximately 72% on the final English-answer capture but still flags individual regions.
  Real bilingual answers and five retrieved passages differ from the illustrative
  image. Some headings are reported missing despite being present in the browser.
  The automated hero phase remains open; do not describe it as passing.
- `DESIGN.md` describes the implemented tokens and
  components. Both YAML and JSON parse successfully.

## Reproducible package

Reviewed overlay: `/tmp/visa-design-release-20261026.zip`, SHA-256
`2625bbc92a790776691e832d9e9b6cb17ee506f7fd144b0b35ff24edf7073184`.
It contains the three web files, Newsreader font and OFL license, and the two
packaging allowlists. It contains no credentials or documents.

In Cloud Shell the previous complete build folder was copied to
`~/visa-design-release-20261026`, then the reviewed overlay was applied.
`gcloud meta list-files-for-upload` matched the public application allowlist,
including both font files: 65 files. The existing build smoke checks cover
1 GiB startup, health with 39 chunks, keyless BM25 search and secret exclusion.

```bash
PROJECT_ID=YOUR_PROJECT_ID
REGION=us-central1
IMAGE="us-central1-docker.pkg.dev/$PROJECT_ID/visa/app:20261026-modern"
gcloud builds submit . --project="$PROJECT_ID" --region="$REGION" \
  --config=cloudbuild.yaml \
  --service-account="projects/$PROJECT_ID/serviceAccounts/visa-builder@$PROJECT_ID.iam.gserviceaccount.com" \
  --gcs-source-staging-dir="gs://$PROJECT_ID-visa-data/build/source" \
  --substitutions="_IMAGE=$IMAGE" --async
```

Build ID: `98dda28c-b2e5-4c0b-9c79-2d0d467c18fa`.
Production build and container smoke checks succeeded. Image digest:
`sha256:b278959ceb17a6bc4508036f0b1a7c172afd214121f8ee024469c8af72887670`.
Live verification is recorded below.

## Cost and retained state

Reuse the existing Cloud Run service, private bucket, Secret Manager reference
and service accounts. Keep minimum zero, maximum one, 1 CPU, 1 GiB, concurrency
one and a 180-second timeout. There is no new database, worker or scheduler.
Build time, stored container images and source archives consume their existing
service allowances. Startup downloads the same snapshot. Gemini remains on the
existing Free-tier project. Free quotas and trial credit do not promise permanent
free hosting. Personal trial balances and expiry dates are omitted from this
public record. Check the billing dashboard before deploying.

## Rollback

Preserve `korea-visa-rag-gemini39` for rollback to the previous UI with Gemini
and the same 39-chunk index:

```bash
gcloud run services update-traffic korea-visa-rag \
  --project=YOUR_PROJECT_ID --region=us-central1 \
  --to-revisions=korea-visa-rag-gemini39=100
```

For a keyless rollback, route to `korea-visa-rag-expanded39` instead. After
rollback, check `/api/health`, the homepage and a cited source search. No data
migration or re-embedding is needed.


## Live verification

Revision `korea-visa-rag-modern` passed candidate checks with AI enabled, 39
chunks and all three search modes. A real E-9 hybrid question returned sources
and citation 1. Homepage, versioned JavaScript and the 109,472-byte bundled font
loaded successfully. Startup logs confirmed the original snapshot SHA and
`vectors: True`. No embeddings were generated during startup.

Public traffic was verified at 100% on `korea-visa-rag-modern`; the temporary
candidate tag is removed. The public browser returned a real E-9 answer and
clicking citation 1 opened its original official passage. Screenshot:
`docs/images/cloud-run-modern.png`. Keep the previous Gemini revision for
rollback. Public URL:
https://korea-visa-rag-jwq77bpivq-uc.a.run.app/.
