# Postman Demo Expectations

## Enrichment timeout/deadline behavior

The triage API is designed to return **partial results** when non-critical enrichment sources are slow or unavailable.

- Each enrichment source call has a per-source timeout (`FLOWRUN_ENRICHMENT_SOURCE_TIMEOUT_S`, default `4.0s`).
- The full enrichment fan-out has an overall deadline (`FLOWRUN_ENRICHMENT_DEADLINE_S`, default `8.0s`).
- If one or more sources time out, triage does **not** hard-fail. The response returns successfully with partial intel.

## Response metadata for monitor assertions

Monitors should validate availability using metadata fields rather than requiring all sources to succeed:

- `timings.total_ms`: End-to-end API processing time in milliseconds.
- `source_summary.available_sources`: Sources that returned usable data.
- `source_summary.failed_sources`: Sources that failed or timed out.
- `warnings[]` (optional): Human-readable non-fatal warnings (for example, timed-out sources or partial enrichment).

## Suggested monitor checks

1. Assert HTTP status is `200` for known-valid IOC payloads.
2. Assert `timings.total_ms` exists and is a non-negative integer.
3. Assert `source_summary.available_sources` is present (may be partial).
4. Allow `source_summary.failed_sources` to be non-empty during upstream incidents.
5. Treat `warnings[]` as diagnostic signal, not a hard failure trigger.

This lets operations monitor agent availability and degraded mode behavior independently from upstream intelligence provider uptime.


## Local reproduction (same checks as CI)

Run these commands from the repository root:

```bash
# 1) Start API in demo mode
export FLOWRUN_DEMO_MODE=true FLOWRUN_NO_PROMPT=1
python -m uvicorn web.app:app --host 127.0.0.1 --port 7777
```

In a second terminal:

```bash
# 2) Install Newman + JUnit reporter (one-time)
npm install -g newman newman-reporter-junitfull

# 3) Optional: enforce health latency threshold (default used in CI: 1000ms)
HEALTH_LATENCY_THRESHOLD_MS=1000
latency_ms=$(curl -o /dev/null -s -w '%{time_total}' http://127.0.0.1:7777/health)
latency_ms=$(python -c "import sys; print(round(float(sys.argv[1])*1000,2))" "$latency_ms")
python -c "import sys; l=float(sys.argv[1]); t=float(sys.argv[2]); assert l<=t, f'Health latency {l}ms exceeds {t}ms'; print(f'Health latency check passed: {l}ms <= {t}ms')" "$latency_ms" "$HEALTH_LATENCY_THRESHOLD_MS"

# 4) Run collection + generate the same artifacts
mkdir -p artifacts/postman
newman run postman_collection.json \
  --env-var baseUrl=http://127.0.0.1:7777 \
  --env-var iocType=domain \
  --reporters cli,json,junitfull \
  --reporter-json-export artifacts/postman/newman-report.json \
  --reporter-junitfull-export artifacts/postman/newman-junit.xml \
  | tee artifacts/postman/newman-cli-summary.txt
```

Pass criteria:
- Newman exits with code `0` (all requests pass).
- Newman reports `0` failed assertions.
- Health latency check passes when threshold is applied.
