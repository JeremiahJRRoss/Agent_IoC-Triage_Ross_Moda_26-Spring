#!/usr/bin/env bash
# Newman wrapper for the FlowRun IoC Triage collection.
#   smoke - fast subset (Liveness + Examples), for pre-commit hooks
#   full  - every folder, all reporters, with an assertion summary
set -euo pipefail

COLLECTION="postman_collection.json"
ENVIRONMENT="postman_environment.demo.json"
mode="${1:-full}"

case "$mode" in
  smoke)
    newman run "$COLLECTION" -e "$ENVIRONMENT" \
      --folder "00 — Liveness" \
      --folder "01 — Examples" \
      --bail
    ;;
  full)
    mkdir -p artifacts/postman
    rc=0
    newman run "$COLLECTION" -e "$ENVIRONMENT" \
      --reporters cli,json,junitfull,htmlextra \
      --reporter-json-export artifacts/postman/newman-report.json \
      --reporter-junitfull-export artifacts/postman/newman-junit.xml \
      --reporter-htmlextra-export artifacts/postman/newman-report.html \
      || rc=$?
    total=$(jq '.run.stats.assertions.total' artifacts/postman/newman-report.json)
    failed=$(jq '.run.stats.assertions.failed' artifacts/postman/newman-report.json)
    duration=$(jq '.run.timings.completed - .run.timings.started' artifacts/postman/newman-report.json)
    echo "════════════════════════════════════════════"
    echo "Newman summary: $total assertions, $failed failed, ${duration}ms wall"
    echo "════════════════════════════════════════════"
    exit "$rc"
    ;;
  *)
    echo "usage: $0 [smoke|full]"
    exit 2
    ;;
esac
