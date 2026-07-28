# Ross Moda IoC Triage API Reference

## Overview

The Ross Moda IoC Triage Agent API accepts an indicator of compromise (IP,
domain, URL, file hash, CVE, or software package) and returns a structured
threat verdict: a weighted composite score, a severity band, recommended
actions, and a per-source intel summary. This document is the human-readable
companion to the live, auto-generated OpenAPI spec served at
[`/docs`](http://localhost:7777/docs) (Swagger UI) and
[`/openapi.json`](http://localhost:7777/openapi.json). When the two disagree,
`/openapi.json` — generated from the Pydantic models in `web/schemas.py` — is
authoritative.

## Base URL & versioning

| Item | Value |
|------|-------|
| Default base URL | `http://localhost:7777` |
| Container/CI base URL | `http://127.0.0.1:7777` |
| API version prefix | `/api/v1` |
| Service version | `0.0.33` (see `info.version` in `/openapi.json`) |

All triage and example endpoints are namespaced under `/api/v1`. The
liveness and UI routes (`/health`, `/`, `/triage`) are unversioned. A future
breaking change to the JSON contract would be published under a new prefix
(`/api/v2`); `/api/v1` responses remain stable within the `0.0.x` line.

## Authentication

**None.** The API ships no authentication or authorization layer. Every
endpoint is open. Do not expose it directly to untrusted networks — place it
behind a reverse proxy or gateway that enforces auth if it must be reachable
outside a trusted boundary. Live mode reads provider API keys from the server
environment (`.env`), never from the request.

## Execution modes

Each `POST /api/v1/triage` call resolves to exactly one execution mode. The
client never selects the mode directly — the server decides it.

| Mode | Trigger | What runs | `execution_mode` | `fixture_id` |
|------|---------|-----------|------------------|--------------|
| `demo` | `IOC_TRIAGE_DEMO_MODE=true` env var | Deterministic fixture lookup under `fixtures/demo/`. No live calls. Missing fixture → `503`. | `"demo"` | fixture key, e.g. `default__ip` |
| `mock` | Request sent to `POST /api/v1/triage/mock` | Returns the canned `fixtures/demo/mock.json` payload. Independent of `IOC_TRIAGE_DEMO_MODE`. | `"mock"` | `"mock"` |
| `live` | Default (no demo env var, normal triage endpoint) | Real LangGraph agent against configured threat-intel integrations. | `"live"` | `null` |

### Precedence

```
            POST /api/v1/triage/mock ─────────────► mock   (always)

            POST /api/v1/triage
                     │
       IOC_TRIAGE_DEMO_MODE=true ? ──── yes ──► demo  (fixture or 503, never live)
                     │
                     no
                     │
                     └─────────────────────► live
```

Precedence is enforced in exactly one place — `web/app.py::triage_api` — and
that is the only code permitted to resolve mode. Demo mode never silently
falls through to live mode: an unresolved fixture is a hard
`503 DEMO_FIXTURE_MISSING`.

## Endpoints

### `GET /health`

Liveness/readiness probe. No agent work, no external calls.

- **Response 200** — `{"status": "ok", "trace_endpoint": <string|null>}`

```bash
curl -s http://127.0.0.1:7777/health
```

### `GET /api/v1/examples/{example_type}`

Returns a ready-to-POST triage request body for the given IOC type, read from
`fixtures/examples/*.json`. This is the single source of truth for sample
payloads — Postman requests chain off it instead of hard-coding JSON.

- **Path parameter** — `example_type`: one of `domain`, `ip`, `hash`, `cve`.
- **Response 200** — `ExampleApiResponse`: `{type, payload: TriageApiRequest, notes}`.
- **Response 404** — `EXAMPLE_NOT_FOUND` (unknown type or missing fixture file).
- **Response 500** — `EXAMPLE_INVALID` (fixture failed schema validation).

```bash
curl -s http://127.0.0.1:7777/api/v1/examples/domain
```

### `POST /api/v1/triage`

Runs IoC triage. Mode resolution per the table above.

- **Request body** — `TriageApiRequest` (JSON).
- **Response 200** — `TriageApiResponse`.
- **Response 400** — `IOC_EMPTY` (IOC empty after trimming).
- **Response 500** — `TRIAGE_FAILED` (live agent raised an exception).
- **Response 503** — `DEMO_FIXTURE_MISSING` (demo mode, no fixture) or `AGENT_UNAVAILABLE` (graph not initialised).

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"8.8.8.8","case_id":"CASE-1002"}'
```

### `POST /api/v1/triage/mock`

Always returns the canned `fixtures/demo/mock.json` payload with
`execution_mode=mock` and `fixture_id=mock`. Independent of
`IOC_TRIAGE_DEMO_MODE`. Use it for schema/contract checks that must not depend on
per-IOC fixtures.

- **Request body** — `TriageApiRequest` (JSON). The `ioc` value is required by
  schema validation but does not affect the canned response.
- **Response 200** — `TriageApiResponse`.
- **Response 503** — `MOCK_FIXTURE_MISSING` (`fixtures/demo/mock.json` absent).

```bash
curl -s -X POST http://127.0.0.1:7777/api/v1/triage/mock \
  -H "Content-Type: application/json" \
  -d '{"ioc":"anything"}'
```

### `GET /` and `POST /triage`

Browser-facing htmx UI. `GET /` serves the single-page form; `POST /triage`
accepts a form-encoded `ioc` field and returns an HTML report fragment. These
are not part of the JSON contract — use `/api/v1/triage` for programmatic
access.

## Response contract: TriageApiResponse

Every successful triage call (`live`, `demo`, or `mock`) returns a
`TriageApiResponse`. Field types are derived from `web/schemas.py`.

| Field | Type | Notes |
|-------|------|-------|
| `case_id` | `string \| null` | Echoes the `case_id` from the request, or `null` if none was sent. |
| `ioc` | `IocIdentity` | `{raw: string, clean: string, type: string}` — original input, normalised value, detected type. |
| `verdict` | `Verdict` | See below. |
| `recommended_actions` | `string[]` | Analyst next steps; content varies with severity. |
| `source_summary` | `SourceSummary` | `{available_sources: string[], failed_sources: string[]}`. |
| `score_breakdown` | `object<string, number>` | Per-source contribution to the composite score. |
| `raw_intel` | `object \| null` | Present only when the request set `include_raw_intel: true`. |
| `report_html` | `string \| null` | Present only when the request set `include_html_report: true`. |
| `trace` | `TraceInfo` | `{trace_endpoint: string \| null}`. |
| `timings` | `Timings` | `{total_ms: integer}` — end-to-end processing time; `0` for fixtures. |
| `warnings` | `string[] \| null` | Non-fatal diagnostics (e.g. timed-out sources). |
| `execution_mode` | `enum` | One of `live`, `demo`, `mock`. |
| `fixture_id` | `string \| null` | Fixture key for `demo`/`mock`; `null` for `live`. |

**`Verdict`**

| Field | Type | Notes |
|-------|------|-------|
| `severity` | `enum` | One of `CLEAN`, `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`. |
| `score` | `number` | Composite threat score, clamped to `[0.0, 1.0]`. |
| `escalation_required` | `boolean` | Whether the verdict warrants escalation. |
| `justification` | `string` | Human-readable rationale. |

**`TriageApiRequest`** (request body for both triage endpoints)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `ioc` | `string` | — | Required, `minLength: 1`. |
| `case_id` | `string \| null` | `null` | Round-tripped into the response unchanged. |
| `source` | `string` | `"manual"` | Free-form provenance label. |
| `include_raw_intel` | `boolean` | `false` | When `true`, populates `raw_intel`. |
| `include_html_report` | `boolean` | `false` | When `true`, populates `report_html`. |

## Error envelope: ApiErrorResponse

All handled errors return a consistent envelope:

```json
{
  "error": {
    "code": "DEMO_FIXTURE_MISSING",
    "message": "demo fixture missing for 'CVE-2021-44228'. Checked: ...",
    "details": null
  },
  "case_id": "CASE-1004",
  "trace": { "trace_endpoint": null }
}
```

`error.details` is an optional object with code-specific context (e.g. the
offending `example_type`). FastAPI request-validation failures (malformed
body) return the framework's default `422` envelope, not this one.

### Canonical error codes

| Code | HTTP | Endpoint(s) | Cause |
|------|------|-------------|-------|
| `IOC_EMPTY` | 400 | `POST /api/v1/triage` | `ioc` is empty/whitespace after trimming. |
| `EXAMPLE_NOT_FOUND` | 404 | `GET /api/v1/examples/{type}` | Unknown IOC type, or the example fixture file is missing. |
| `EXAMPLE_INVALID` | 500 | `GET /api/v1/examples/{type}` | Example fixture exists but failed `TriageApiRequest` validation. |
| `DEMO_FIXTURE_MISSING` | 503 | `POST /api/v1/triage` (demo) | No demo fixture resolves for the IOC. Never falls through to live. |
| `MOCK_FIXTURE_MISSING` | 503 | `POST /api/v1/triage/mock` | `fixtures/demo/mock.json` is absent. |
| `AGENT_UNAVAILABLE` | 503 | `POST /api/v1/triage` (live) | The LangGraph agent was not initialised at startup. |
| `TRIAGE_FAILED` | 500 | `POST /api/v1/triage` (live) | The live agent raised an unexpected exception. |

## Quickstart curls

```bash
# 1. Liveness
curl -s http://127.0.0.1:7777/health

# 2. Fetch a canonical example payload
curl -s http://127.0.0.1:7777/api/v1/examples/ip

# 3. Demo-mode triage (server started with IOC_TRIAGE_DEMO_MODE=true)
curl -s -X POST http://127.0.0.1:7777/api/v1/triage \
  -H "Content-Type: application/json" \
  -d '{"ioc":"8.8.8.8","case_id":"CASE-1002"}'

# 4. Mock-mode triage (schema-only contract check)
curl -s -X POST http://127.0.0.1:7777/api/v1/triage/mock \
  -H "Content-Type: application/json" \
  -d '{"ioc":"anything"}'
```

## Cross-references

- [`docs/POSTMAN_DEMO.md`](POSTMAN_DEMO.md) — Newman/Postman runbook, worked
  scenarios, and CI parity instructions.
- [`docs/POSTMAN_PRESENTATION.md`](POSTMAN_PRESENTATION.md) — presenter script
  for the live Postman demo.
- [`web/schemas.py`](../web/schemas.py) — the authoritative Pydantic contract.
  Every field and type in this document is derived from it.
- [`/docs`](http://localhost:7777/docs) — interactive Swagger UI with
  "Try it out" and pre-filled example payloads.
