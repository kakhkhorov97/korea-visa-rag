#!/usr/bin/env bash
# Manual GitHub Actions release. The existing Cloud Run service keeps its secrets,
# runtime identity, pinned snapshot and limits; only its container image changes.
set -euo pipefail

test "${GITHUB_ACTIONS:-}" = true
test "${GITHUB_REPOSITORY:-}" = kakhkhorov97/korea-visa-rag
test "${GITHUB_REF:-}" = refs/heads/main
test -n "${PROJECT_ID:-}"
test -n "${REGION:-}"
test -n "${SERVICE:-}"
test -n "${GITHUB_SHA:-}"

BUCKET="${PROJECT_ID}-visa-data"
BUILD_SA="visa-builder@${PROJECT_ID}.iam.gserviceaccount.com"
RUNTIME_SA="visa-runtime@${PROJECT_ID}.iam.gserviceaccount.com"
IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/visa/app:gha-${GITHUB_SHA:0:12}-${GITHUB_RUN_ID}"

# The image and persisted index must describe the same reviewed public corpus.
# A corpus update needs a separately reviewed snapshot and an updated release gate.
test "$(find data/public_raw -maxdepth 1 -name '*.txt' | wc -l | tr -d ' ')" = 44
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --format=json > service-before.json
export RUNTIME_SA
GOOD_REVISION="$(python3 - <<'PY'
import json, os
service = json.load(open('service-before.json'))
template = service['spec']['template']['spec']
assert template['serviceAccountName'] == os.environ['RUNTIME_SA']
env = {item['name']: item.get('value') for item in template['containers'][0]['env']}
assert env['VISARAG_PUBLIC_BETA'].lower() == 'true'
assert env['VISARAG_SNAPSHOT_SHA256'] == 'dde1fed36a8d42e06a10b29a84b32054a3dfbfbd0c16912c2c812f6bc80cb477'
assert env['VISARAG_SNAPSHOT_GENERATION'] == '1793023155930292'
assert env['VISARAG_SNAPSHOT_URI'].endswith('/releases/' + env['VISARAG_SNAPSHOT_SHA256'] + '.json')
assert env['VISARAG_USAGE_URI'].endswith('/usage/public-beta')
assert any(item['name'] == 'GEMINI_API_KEY' and 'valueFrom' in item for item in template['containers'][0]['env'])
traffic = [item['revisionName'] for item in service['status']['traffic'] if item.get('percent') == 100]
assert len(traffic) == 1, 'Expected exactly one live revision'
print(traffic[0])
PY
)"
test -n "$GOOD_REVISION"

# The checked-in allowlist excludes credentials, private documents and local indexes.
gcloud builds submit . --project="$PROJECT_ID" --region="$REGION" \
  --config=cloudbuild.beta.yaml --substitutions="_IMAGE=${IMAGE}" \
  --service-account="projects/${PROJECT_ID}/serviceAccounts/${BUILD_SA}" \
  --gcs-source-staging-dir="gs://${BUCKET}/build/source" \
  --ignore-file=.gcloudignore
DIGEST="$(gcloud artifacts docker images describe "$IMAGE" --project="$PROJECT_ID" --format='value(image_summary.digest)')"
test -n "$DIGEST"
PINNED_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/visa/app@${DIGEST}"
echo "Built pinned image: ${PINNED_IMAGE}"

# A tagged candidate is publicly reachable, but the primary URL stays on the
# known-good revision until all checks below pass.
gcloud run deploy "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --image="$PINNED_IMAGE" --service-account="$RUNTIME_SA" \
  --no-traffic --tag=ci-candidate
gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --format=json > service-candidate.json
read -r CANDIDATE_REVISION CANDIDATE_URL < <(python3 - <<'PY'
import json
service = json.load(open('service-candidate.json'))
candidate = [item for item in service['status']['traffic'] if item.get('tag') == 'ci-candidate']
assert len(candidate) == 1 and candidate[0].get('percent', 0) == 0
print(candidate[0]['revisionName'], candidate[0]['url'])
PY
)
test -n "$CANDIDATE_REVISION"
test -n "$CANDIDATE_URL"

curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 5 \
  "$CANDIDATE_URL/api/health" > candidate-health.json
python3 - <<'PY'
import json
health = json.load(open('candidate-health.json'))
assert health['status'] == 'ok' and health['chunks'] == 44
assert health['llm'] and {'bm25', 'vector', 'hybrid'} <= set(health['modes'])
assert health['ai_ack_required'] and health['shared_limits']
PY
curl --fail --silent --show-error "$CANDIDATE_URL/" > candidate-home.html
grep -q '/static/favicon.svg' candidate-home.html
curl --fail --silent --show-error "$CANDIDATE_URL/static/favicon.svg" > candidate-favicon.svg
grep -q '<svg' candidate-favicon.svg
curl --fail --silent --show-error "$CANDIDATE_URL/privacy" > /dev/null
curl --fail --silent --show-error -H 'Content-Type: application/json' \
  -d '{"question":"D-10 구직","source_only":true}' "$CANDIDATE_URL/api/ask" > candidate-answer.json
python3 - <<'PY'
import json
answer = json.load(open('candidate-answer.json'))
assert answer['mode'] == 'search-only' and answer['sources']
assert all(source['url'].startswith('https://www.law.go.kr/') for source in answer['sources'])
PY
test "$(curl --silent --show-error -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' -d '{"question":"What is D-10?"}' \
  "$CANDIDATE_URL/api/ask")" = 403
test "$(curl --silent --show-error -o /dev/null -w '%{http_code}' \
  -H 'Content-Type: application/json' \
  -d '{"question":"Contact me at test@example.com","source_only":true}' \
  "$CANDIDATE_URL/api/ask")" = 422
curl --fail --silent --show-error -H 'Content-Type: application/json' \
  -d '{"question":"What is the maximum stay for D-10?","ai_ack":true}' \
  "$CANDIDATE_URL/api/ask" > candidate-ai-answer.json
python3 - <<'PY'
import json
answer = json.load(open('candidate-ai-answer.json'))
assert answer['mode'] != 'search-only', 'AI failed or grounding returned a source fallback'
assert answer['cited'] and answer['evidence'], 'AI answer lacks checked citations'
PY

# Promote only after the candidate passes. If public verification fails, restore
# the revision that served 100% of traffic before this run.
gcloud run services update-traffic "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
  --to-revisions="${CANDIDATE_REVISION}=100"
PUBLIC_URL="$(gcloud run services describe "$SERVICE" --project="$PROJECT_ID" --region="$REGION" --format='value(status.url)')"
if ! curl --fail --silent --show-error --retry 5 --retry-all-errors --retry-delay 5 \
  "$PUBLIC_URL/api/health" > public-health.json || \
  ! cmp -s candidate-health.json public-health.json || \
  ! curl --fail --silent --show-error "$PUBLIC_URL/static/favicon.svg" > /dev/null; then
  gcloud run services update-traffic "$SERVICE" --project="$PROJECT_ID" --region="$REGION" \
    --to-revisions="${GOOD_REVISION}=100"
  exit 1
fi
echo "Deployed ${GITHUB_SHA} as ${CANDIDATE_REVISION}; prior revision ${GOOD_REVISION} is available for rollback."
