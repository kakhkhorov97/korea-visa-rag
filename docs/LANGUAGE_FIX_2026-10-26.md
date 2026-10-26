# Answer-language correction

## Change

The old prompt said to match the question language but placed the question next
to Korean source passages. The selected language now comes from the question
alone and is explicit in both the system instruction and the end of the user
prompt. A mostly wrong-script reply raises a safe error instead of returning
it as an answer. Short Korean terms and original source labels remain allowed.

The shared assistant serves both web and Telegram. Retrieval, citations,
source-only safeguards, keyless search, the public corpus and its saved vectors
are unchanged. Provider calls remain isolated in `llm.py`. No automatic retry
or translation call was added. The longer prompt consumes some extra input
tokens. Mixed-language detection and script validation are heuristics, not a
promise of perfect language recognition or legal accuracy.

This follows Google's guidance to put critical constraints in system
instructions: [Gemini prompt design](https://ai.google.dev/gemini-api/docs/prompting-strategies).

## Verification

- 93 Python tests passed with real libraries. New cases cover English/Korean
  selection, mixed terms, visa codes, source-language independence and rejection
  without automatic retries.
- Five Node browser-rendering tests still pass.
- Four real local Gemini calls passed in BM25 mode. English E-9 and D-2 questions
  and an English question containing 비전문취업 returned English explanations;
  a Korean E-9 question returned Korean. All four retained citation 1.
- These are focused functional checks, not an answer-quality benchmark.

## Reproducible cloud build

The tested `src/visarag/assistant.py` SHA-256 is
`5e48f2998bcb364be0a8dbfab2a46ede69972ff62d20cc84c6aaef2f594a7da4`.
Cloud Shell applied the module-only patch to a copy of the previous release and
verified that exact hash before building. The public upload allowlist is checked
before submission. The one-file image uses the immutable, previously verified
modern image, preserving installed dependency versions:

```dockerfile
FROM us-central1-docker.pkg.dev/project-a5074080-2d38-4a35-8b4/visa/app@sha256:b278959ceb17a6bc4508036f0b1a7c172afd214121f8ee024469c8af72887670
COPY src/visarag/assistant.py /app/src/visarag/assistant.py
```

The normal repository Dockerfile also includes this source change on a full
build. The release folder is `~/visa-language-release-20261026`; its Dockerfile
uses the two lines above. Submission uses the existing `cloudbuild.yaml`, builder
service account and staging bucket with image tag `20261026-language`. The
existing keyless 1 GiB health, source-search and secret-exclusion smoke checks
must pass before deployment. No Git mutation is part of this work.

## Rollback

To restore the preceding modern UI and backend:

```bash
gcloud run services update-traffic korea-visa-rag \
  --project=project-a5074080-2d38-4a35-8b4 --region=us-central1 \
  --to-revisions=korea-visa-rag-modern=100
```

Keep the existing min-zero/max-one limits, secret version, runtime identity and
snapshot reference. No data migration or embedding generation is required.
Build, image storage and runtime usage remain subject to existing allowances;
no billing upgrade or paid AI activation is authorized by this fix.

## Build outcome

Cloud Build `7cd37933-2d6a-493c-8f36-a9d11f56caad` succeeded, including its
container smoke checks. Result image:
`us-central1-docker.pkg.dev/project-a5074080-2d38-4a35-8b4/visa/app@sha256:d73d620784cb2b40302ab9bfe24ab28eb7c0b415a5a4254ceeb1b883b78851b1`.

## Published verification

Revision `korea-visa-rag-language` receives 100% of public traffic. The temporary
`languagecheck` tag was removed. Candidate hybrid-mode tests returned English
for E-9 and D-2 English questions and Korean for the Korean E-9 question, all
with citation 1. Health reports 39 chunks and hybrid/BM25/vector available.
Startup logs confirm the same snapshot SHA and `vectors: True`.

A further public-browser E-9 question returned an English explanation with a
working official source reference. Screenshot:
`docs/images/cloud-run-language-fix.png`. Original source titles and the source
panel remain Korean, matching the official documents.

Public URL: https://korea-visa-rag-jwq77bpivq-uc.a.run.app/.
No files were staged, committed or pushed.
