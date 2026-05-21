# 🛡️ FlowRun Streamlet: IoC Triage

**v0.0.33 · LangGraph · LangChain · OpenAI GPT-4o · OpenTelemetry · contract-tested with Postman**

A security analyst confronted with a suspicious IP address has a familiar sequence of moves: check VirusTotal, check AbuseIPDB, check AlienVault OTX, sometimes urlscan.io, sometimes NVD, write up the verdict, decide whether to escalate. The process takes ten to twenty-five minutes per indicator, and most of those minutes are spent waiting on browser tabs to load. FlowRun is what happens when you compress that sequence into thirty seconds and add a full trace of every decision.

This is a working agent. The interesting part — the part this repository exists to make visible — is not the agent itself but the testing surface around it.

---

## What this repository is, and why it ships with a Postman demo

Most security tools at this layer are tested by the team that built them and validated by the team that runs them. The contract between the two — what the API actually returns, what the response shapes look like, when a failure mode fires — tends to live in someone's head, then in a wiki, then in a Slack thread, then back in someone's head. By the time the agent is in production, the contract has drifted from the documentation, and the documentation has drifted from the code.

This repository takes a different position. The contract is the OpenAPI document the server emits at `/openapi.json`. The tests are a Postman collection that derives its schemas from that document at runtime. The CI pipeline runs the same collection on every push. Local development runs the same collection in a Postman GUI. Newman — Postman's headless engine — runs it from a pre-commit hook. Three environments, one artifact, no drift.

If you are here because you want to evaluate the agent, start with the [Quick Start](#quick-start). If you are here because you want to evaluate the testing approach — which is the more interesting story — go straight to [`demo/POSTMAN_SETUP.md`](demo/POSTMAN_SETUP.md).

---

## Two ways to run the service

The service has two operating modes that share a single Postman collection. The distinction matters before you do anything else.

**Demo mode** (`FLOWRUN_DEMO_MODE=true`) reads triage responses from JSON fixtures baked into the container. The LangGraph agent never runs. No outbound call leaves the container. No API key is required. Responses are deterministic, fast, and identical across machines. This is the mode used in the Postman demo, in CI, on a clean evaluator's laptop, and in any environment where you want to validate the testing pattern itself rather than the threat-intel results. Demo mode exists because the *testing approach* is the contribution, and showing the approach reliably requires that the wire not surprise you.

**Live mode** is the default and what production uses. The LangGraph agent runs, queries up to nine threat-intelligence APIs in parallel, weights and correlates the responses, and returns a real verdict. Live mode needs five API keys — OpenAI, VirusTotal, AbuseIPDB, OTX, urlscan.io — in a local `.env` file. Live mode is what the testing pattern is *for*; demo mode is how you prove the testing pattern without depending on any vendor during a presentation.

Both modes return the same response shape. The schema assertions pass against either. The only field that differs is `execution_mode`, which carries `live`, `demo`, or `mock`, and the Postman collection asserts it equals the value of `expectedExecutionMode` in the active environment. That single field is the bright line between the two modes at the test layer — provable, not conventional.

---

## What the agent does

You submit an indicator of compromise — an IP address, a domain, a URL, a file hash (MD5, SHA-1, or SHA-256), a CVE identifier, or a software package (prefixed like `npm:postmark-mcp`, or bare like `traceroute` for a multi-ecosystem scan). The agent classifies it, fans out to every applicable threat-intelligence source in parallel, normalizes each response onto a 0.0–1.0 axis, applies a weighted composite formula, and maps the result onto five severity bands: CLEAN, LOW, MEDIUM, HIGH, CRITICAL. CRITICAL pauses for human confirmation before releasing. Everything else streams through to a structured report.

The pipeline is built on LangGraph (state machine), LangChain (tool wrappers), OpenAI `gpt-4o-mini` (classification, temperature 0.0) and `gpt-4o` (correlation summary, temperature 0.3), and OpenTelemetry through the Traceloop SDK (auto-instrumentation, OTLP/HTTP export). The agent ships as a FastAPI application on port `7777` with a small htmx web UI and a complete JSON API under `/api/v1/`.

For the architecture in full, see [`docs/FlowRun_Streamlet_IoC_Triage_Architecture_v2.md`](docs/FlowRun_Streamlet_IoC_Triage_Architecture_v2.md). For the requirements that drove it, see [`docs/FlowRun_Streamlet_IoC_Triage_PRD_v2.md`](docs/FlowRun_Streamlet_IoC_Triage_PRD_v2.md).

---

## Quick start

The service runs as a container on port `7777`. Works identically with Docker (20.10+) or Podman (4.0+).

```bash
# Optional: provide API keys for live mode. Demo mode needs none.
cp .env.template .env   # then fill in the five required keys

# Build and start, demo mode (no keys needed)
FLOWRUN_DEMO_MODE=true docker compose up --build -d

# Confirm
curl http://127.0.0.1:7777/health
```

Open <http://localhost:7777>. Paste an IOC — `8.8.8.8`, `malware.wicar.org`, `CVE-2021-44228`, `npm:postmark-mcp` — and click **Triage**. The report renders inline.

To run in live mode, drop the `FLOWRUN_DEMO_MODE` variable:

```bash
docker compose up --build -d
```

Stop the stack:

```bash
docker compose down
```

For the full setup walkthrough — including the wrapper script that auto-detects Docker or Podman, the optional OpenTelemetry collector configuration, and a troubleshooting table — see [`QUICK_START.md`](QUICK_START.md).

---

## The Postman testing surface

The collection at `postman_collection.json` carries thirty-seven assertions across five folders. The assertions fall into four pillars:

**Liveness** is one request — `GET /health` — and asserts the response is shape-correct, status 200, and below a 200-millisecond latency budget. Liveness exists so an orchestrator can ask the cheapest possible question.

**Contract** validates every triage response against the OpenAPI schema. A collection-level pre-request script fetches `/openapi.json` once per run and caches the `components.schemas` block. Every contract assertion compiles `TriageApiResponse` with AJV and validates the body. When a developer edits a Pydantic model in `web/schemas.py`, the OpenAPI document changes on the next server restart, and the next collection run picks it up automatically. There is no separate schema to keep synchronized.

**Behavior** asserts that the three execution modes — `live`, `demo`, and `mock` — stay separated at runtime. A demo-mode request must return `execution_mode: "demo"` and a non-empty `fixture_id`. The same collection points at a live server through a different environment file and the corresponding assertion verifies `execution_mode: "live"` and `fixture_id: null`.

**Negative paths** assert the failure modes. Empty IOC returns `400 IOC_EMPTY`. Unknown example type returns `404 EXAMPLE_NOT_FOUND`. A CVE submitted in demo mode — with no fixture available — returns `503 DEMO_FIXTURE_MISSING`. That last assertion is the proof that demo mode and live mode are provably distinct: demo mode never silently falls through to a live API call.

To set up Postman from a clean machine — including importing the collection, choosing between demo and live environments, and wiring up CI — see [`demo/POSTMAN_SETUP.md`](demo/POSTMAN_SETUP.md). To deliver the live four-minute demo, see [`demo/POSTMAN_DEMO_INSTRUCTIONS.md`](demo/POSTMAN_DEMO_INSTRUCTIONS.md) (mechanics) and [`demo/POSTMAN_DEMO_SCRIPT.md`](demo/POSTMAN_DEMO_SCRIPT.md) (narration).

---

## CI: the same collection, on every push

A GitHub Actions workflow at `.github/workflows/postman.yml` runs `postman_collection.json` against a freshly booted server on every push and every pull request. The job boots `uvicorn` directly with `FLOWRUN_DEMO_MODE=true`, polls `/health` until the FastAPI lifespan hook finishes, asserts the latency budget on `/health`, runs the full collection through Newman with four reporters, and gates the build on two `jq` checks against the JSON report:

```bash
test "$total"  -ge 25      # the suite must have at least 25 assertions
test "$failed" -eq 0       # all of them must pass
```

The assertion-count gate exists to prevent the suite from being silently neutered. The failure gate is the obvious one. Either condition exits the job non-zero, which fails the build, which (with a branch protection rule) blocks the pull request from merging.

Artifacts upload with `if: always()` — JUnit XML, JSON, HTML, CLI summary, and the server's stdout — so debugging data exists whether the run passed or failed.

To trigger the workflow from the command line, or to download artifacts from a failed run without leaving the terminal, install the [GitHub CLI](https://cli.github.com) and use `gh workflow run postman.yml`, `gh run watch`, and `gh run view --log-failed`. The setup guide covers the full flow.

---

## API in one paragraph

The full reference is at [`docs/API.md`](docs/API.md), and the live OpenAPI documentation is at `/docs` when the server is running. The shape is small. Three triage endpoints — `POST /api/v1/triage` for either live or demo mode (the server decides based on environment), `POST /api/v1/triage/mock` for schema-only contract checks against a canned payload, and `GET /api/v1/examples/{type}` for canonical sample payloads sourced from `fixtures/examples/`. One liveness endpoint at `/health`. One browser UI at `/`. Every error response uses the same envelope: `{"error": {"code": "...", "message": "...", "details": {...}}}`. Every successful triage response carries `execution_mode` and (for demo/mock) `fixture_id`, so consumers can assert which mode produced the result.

---

## Documentation map

| Document | What it answers |
|---|---|
| [`QUICK_START.md`](QUICK_START.md) | How do I get the service running locally? |
| [`demo/POSTMAN_SETUP.md`](demo/POSTMAN_SETUP.md) | How do I set up Postman from a clean machine, including CI? |
| [`demo/POSTMAN_DEMO_INSTRUCTIONS.md`](demo/POSTMAN_DEMO_INSTRUCTIONS.md) | The click-by-click runbook to keep open during the live demo |
| [`demo/POSTMAN_DEMO_SCRIPT.md`](demo/POSTMAN_DEMO_SCRIPT.md) | The presenter narration, with timing and technical depth |
| [`docs/API.md`](docs/API.md) | Endpoints, schemas, error codes, execution modes |
| [`docs/FlowRun_Streamlet_IoC_Triage_PRD_v2.md`](docs/FlowRun_Streamlet_IoC_Triage_PRD_v2.md) | Functional and non-functional requirements |
| [`docs/FlowRun_Streamlet_IoC_Triage_Architecture_v2.md`](docs/FlowRun_Streamlet_IoC_Triage_Architecture_v2.md) | Layered architecture, state schema, integration design |
| [`docs/FlowRun_Streamlet_IoC_Triage_User_Manual_v2.md`](docs/FlowRun_Streamlet_IoC_Triage_User_Manual_v2.md) | End-user manual for the web UI |
| [`docs/ERD.md`](docs/ERD.md) | Entity relationships across the pipeline |
| `postman_collection.json` | The Postman collection itself |
| `postman_environment.demo.json` / `postman_environment.local.json` | Environment values for demo and live mode |
| `.github/workflows/postman.yml` | The CI pipeline |

---

## Project structure

```
flowrun-streamlet-ioc-triage/
├── compose.yaml              Docker/Podman compose — default deployment
├── Dockerfile                Python 3.11-slim, uvicorn on port 7777
├── flowrun_agent.py          CLI entry point (legacy; the container is the default)
├── flowrun_agent.ipynb       Jupyter notebook (8 cells, demo-friendly)
├── requirements.txt          Top-level dependencies
├── requirements.lock         Pinned tree (uv-resolved)
│
├── web/
│   ├── app.py                FastAPI app — UI + JSON API
│   ├── schemas.py            Pydantic models — the contract source
│   ├── response_mapper.py    Internal-state → public-DTO adapter
│   ├── demo_mode.py          Fixture loading for demo and mock modes
│   ├── templates/index.html  htmx single-page form
│   └── static/style.css
│
├── agent/
│   ├── graph.py              LangGraph StateGraph
│   ├── state.py              AgentState TypedDict
│   ├── llm.py                MODEL_CONFIG — single point to swap models
│   ├── scoring.py            Weighted scoring, normalisers, conflict detection
│   ├── report.py             CLI text and HTML report formatters
│   ├── credentials.py        .env → os.environ → getpass() resolution
│   ├── tracing.py            OpenTelemetry / Traceloop setup
│   ├── tools/                LangChain tool wrappers (one per source)
│   └── integrations/         Raw HTTP clients and response parsers
│
├── fixtures/
│   ├── demo/                 Deterministic fixtures for demo mode
│   └── examples/             Canonical example payloads for the API
│
├── tests/                    pytest suite (164+ tests)
├── docs/                     PRD, architecture, API, user manual, ERD
├── demo/                     Postman setup, demo runbook, presenter script
└── scripts/
    ├── compose.sh            Auto-detects Docker or Podman
    └── postman.sh            Newman wrapper — smoke and full modes
```

---

## Changing models

All model configuration lives in `agent/llm.py`. To swap models, edit `MODEL_CONFIG`:

```python
MODEL_CONFIG = {
    "classifier": {"model": "gpt-4o-mini", "temperature": 0.0},
    "report":     {"model": "gpt-4o",      "temperature": 0.3},
}
```

No other file needs to change.

---

## Changelog

**v0.0.33 — Containerized default deployment + web UI**
- The container is now the default install path. `docker compose up --build -d` (or the Podman equivalent) builds and starts the stack.
- FastAPI web UI on port `7777` (`web/app.py`) with an htmx-driven form. Reuses the existing LangGraph; the HTML report formatter is unchanged.
- `/health` endpoint added for container liveness probes; built-in `HEALTHCHECK` in the image.
- `FLOWRUN_NO_PROMPT=1` skips `getpass()` so the agent fails fast in non-interactive environments instead of hanging.
- Default OTLP destination is `http://host.docker.internal:4318`, reachable on Docker Desktop and rootless Podman via `extra_hosts: host-gateway`.
- CLI (`python flowrun_agent.py`) and the Jupyter notebook continue to work unchanged.
- Postman collection and CI workflow added — contract testing on every push.

**v0.0.32 — Vendor-neutral tracing**
- Removed Arize-specific dependencies. Added standard OpenTelemetry SDK + Traceloop SDK (OpenLLMetry). Auto-instruments LangChain, LangGraph, and OpenAI.
- Required keys reduced from seven to five. OpenTelemetry configuration is fully optional.

**v0.0.31 — Package supply chain analysis**
- New IOC types: `package` (prefixed `ecosystem:name`) and `package_multi` (bare name, scanned across ten ecosystems).
- New data sources: OSV.dev (Google) for known malicious packages and vulnerabilities; npm/PyPI registry metadata for age, maintainers, install scripts, source repo signals.
- Twenty-seven supported ecosystems including major Linux distributions.

**v0.0.26 — Enhanced report intelligence**
- Per-engine AV detection names for hash IOCs.
- OTX threat actor and campaign tag extraction in findings.
- CVSS severity string and attack vector for CVE reports.
- Conflicting-signal callout when sources disagree.
- TL;DR one-line summary and timestamp on every report.

**v0.0.24 — URL-to-domain dual-query enrichment**
- When a URL is submitted, the domain is also queried against VirusTotal and OTX. The stronger threat signal wins.
- Domains are sent to urlscan.io for live browser analysis.

**v0.0.21 — Scoring sensitivity fix**
- VirusTotal normalizer now uses a non-linear detection-count curve. A few malicious detections in a corpus of ninety engines correctly produce a MEDIUM or higher score, matching analyst expectations.

**v0.2 — Runtime compatibility fixes**
- Tracing init corrected to use `project_name`.
- Domain IOCs classified by regex; LLM fallback no longer required for the common case.
- Model config uses actual available models.

---

## License

MIT. See [`LICENSE`](LICENSE).
