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


## Demo modes

`POST /api/v1/triage` resolves exactly one execution mode per request. The
client never picks the mode — the server decides it. The collection asserts
the resolved mode on every triage request.

| Mode | Trigger condition | What runs | `execution_mode` | `fixture_id` |
|------|-------------------|-----------|------------------|--------------|
| `live` | Default — no `FLOWRUN_DEMO_MODE`, normal triage endpoint | Real LangGraph agent against configured threat-intel integrations | `"live"` | `null` |
| `demo` | `FLOWRUN_DEMO_MODE=true` env var set on the server | Deterministic fixture lookup under `fixtures/demo/`; missing fixture → hard `503` | `"demo"` | fixture key, e.g. `default__domain`, `default__ip` |
| `mock` | Request sent to `POST /api/v1/triage/mock` | Returns the canned `fixtures/demo/mock.json` payload, independent of `FLOWRUN_DEMO_MODE` | `"mock"` | `"mock"` |

Precedence is strict: in demo mode an unresolved fixture is a
`503 DEMO_FIXTURE_MISSING`, never a silent fall-through to a live call.


## Worked scenarios

All commands assume a server started with `FLOWRUN_DEMO_MODE=true` on
`127.0.0.1:7777`. Expected-output blocks are truncated for brevity.

### 1. Healthy triage of a known fixture (`domain`)

Why it matters: proves the demo happy path — a fixtured IOC returns a complete
`TriageApiResponse` with `execution_mode=demo`.

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"malware.wicar.org","case_id":"CASE-1001"}'
```

```json
{
  "case_id": "CASE-1001",
  "ioc": {"raw": "malware.wicar.org", "clean": "malware.wicar.org", "type": "domain"},
  "verdict": {"severity": "MEDIUM", "score": 0.55, "escalation_required": false},
  "execution_mode": "demo",
  "fixture_id": "default__domain"
}
```

### 2. Schema-only validation via mock mode

Why it matters: `POST /api/v1/triage/mock` always returns the same canned
payload, so contract/schema checks never depend on per-IOC fixtures.

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage/mock \
  -H "Content-Type: application/json" \
  -d '{"ioc":"schema-check.example"}'
```

```json
{
  "ioc": {"raw": "example.local", "clean": "example.local", "type": "domain"},
  "verdict": {"severity": "LOW", "score": 0.2},
  "execution_mode": "mock",
  "fixture_id": "mock"
}
```

### 3. Fixture miss in demo mode → 503

Why it matters: proves mode precedence is strict. A CVE is classified fine but
has no demo fixture — demo mode hard-fails instead of degrading to a live call.

```bash
curl -s -o /dev/null -w "%{http_code}\n" -X POST \
  http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"CVE-2021-44228"}'
```

```json
{
  "error": {
    "code": "DEMO_FIXTURE_MISSING",
    "message": "demo fixture missing for 'CVE-2021-44228'. Checked: cve__cve-2021-44228, default__cve"
  }
}
```

### 4. Empty IOC → 400

Why it matters: a whitespace-only IOC passes Pydantic `minLength` but is
rejected by the handler with a structured `IOC_EMPTY` error.

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"   "}'
```

```json
{
  "error": {"code": "IOC_EMPTY", "message": "IOC must not be empty", "details": null},
  "case_id": null,
  "trace": {"trace_endpoint": null}
}
```

### 5. `case_id` propagation

Why it matters: a `case_id` supplied in the request is echoed back verbatim,
letting a SOC correlate a triage result with its originating case.

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"8.8.8.8","case_id":"CASE-ROUNDTRIP-7777"}'
```

```json
{
  "case_id": "CASE-ROUNDTRIP-7777",
  "ioc": {"raw": "8.8.8.8", "clean": "8.8.8.8", "type": "ip"},
  "execution_mode": "demo",
  "fixture_id": "default__ip"
}
```


## Reading the artifacts

A full Newman run writes three artifacts under `artifacts/postman/`:

- **`newman-junit.xml`** — JUnit XML. Each `<testcase>` is one `pm.test(...)`
  assertion; its `name` is the assertion label and its parent `<testsuite>` is
  the request. A `<failure>` child marks a failed assertion. CI test-result
  viewers and IDEs parse this file directly.
- **`newman-report.json`** — the machine-readable run report. The key object is
  `run.stats.assertions` (`{total, pending, failed}`); `run.failures[]` lists
  any failed assertions with their error. The CI assertion-count gate reads
  `total` and `failed` from here.
- **`newman-cli-summary.txt`** — the plain-text CLI summary (the boxed table
  Newman prints). This is where a human looks **first** — it shows the per-folder
  pass/fail ticks and the final totals at a glance.


## Maintenance

How the optimized collection is wired, for future maintainers.

### Schema validation

Triage success responses are validated against the live OpenAPI schema, not a
hand-written copy. The collection-level pre-request script in
`postman_collection.json` (`event` → `prerequest`) calls
`pm.sendRequest(${baseUrl}/openapi.json)` once per run and stores
`components.schemas` in the `openApiSchemas` collection variable. Each triage
success request's test then compiles `components.schemas.TriageApiResponse`
with `ajv` (bundled in the Newman sandbox) and validates the response body. A
field-type change in `web/schemas.py` flows into `/openapi.json` automatically,
so the assertion tracks the code with no manual edit.

### Response-time budgets

Each request carries an inline `responseTime` budget assertion in its test
script (`pm.expect(pm.response.responseTime).to.be.below(N)`). Budgets by
folder: `00 — Liveness` 200ms, `01 — Examples` 300ms, `02 — Triage (demo)`
500ms, `03 — Triage (mock)` 300ms, `04 — Negative & contract` 500ms. To
retune one, edit the `below(...)` value in the relevant request's
`event` → `test` → `script.exec` block in `postman_collection.json`.

### Smoke vs full

`scripts/postman.sh` wraps Newman:

- `./scripts/postman.sh smoke` — runs only `00 — Liveness` and `01 — Examples`
  with `--bail`. Fast (~1s); suitable for a pre-commit hook.
- `./scripts/postman.sh full` — runs every folder, emits the `cli`, `json`,
  `junitfull`, and `htmlextra` reporters into `artifacts/postman/`, and prints
  an assertion-count summary line. This is what CI runs.

### HTML reporter

`./scripts/postman.sh full` writes `artifacts/postman/newman-report.html`
(via `newman-reporter-htmlextra`). Open it in a browser for a per-request,
per-assertion drill-down with request/response bodies — the artifact reviewers
open when a CI run needs investigating.

### Adding a new endpoint test

1. Add the route to `web/app.py` with full metadata (`tags`, `summary`,
   `description`, `responses`); document it in `docs/API.md`.
2. If the endpoint needs demo data, add a fixture under `fixtures/demo/` or
   `fixtures/examples/` (see `web/demo_mode.py` for the lookup rules).
3. Add a request item to the matching folder's `item` array in
   `postman_collection.json`, with a `url` and (for POST) a JSON `body`.
4. Add an `event` with `listen: "test"`; assert at minimum the status code,
   and add a folder-appropriate `responseTime` budget. For triage-shaped
   responses, also add the `ajv` schema check and the `triageResponseKeys`
   membership check used in `02 — Triage (demo mode)`.
5. Run `./scripts/postman.sh full` and confirm the CI assertion-count gate in
   `.github/workflows/postman.yml` still passes (`total >= 25`, `failed == 0`).
