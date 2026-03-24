#!/usr/bin/env bash
# Runpod Console -> Endpoint -> ID ve API Key (Bearer) gerekir.
# Kullanim: RUNPOD_ENDPOINT_ID=xxx RUNPOD_API_KEY=rpa_xxx ./examples/runpod_curl_runsync.sh

set -euo pipefail
: "${RUNPOD_ENDPOINT_ID:?EXPORT RUNPOD_ENDPOINT_ID}"
: "${RUNPOD_API_KEY:?EXPORT RUNPOD_API_KEY}"

REQ="$(cd "$(dirname "$0")" && pwd)/runpod_runsync.json"

curl -sS -X POST "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d @"${REQ}"

echo
