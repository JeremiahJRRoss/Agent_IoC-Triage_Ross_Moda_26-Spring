# 🛡️ FlowRun Streamlet: IoC Triage — v0.0.33

Automated Threat Intelligence Triage for Security Operations.

Built with **LangGraph** + **LangChain** + **OpenAI GPT-4o** + **OpenTelemetry (Traceloop)**.

## What It Does

Submit any IOC (IP address, domain, URL, file hash, CVE identifier, or **software package**) and the agent will:

1. Classify the IOC type automatically
2. Query up to 7 threat intelligence APIs **in parallel** (VirusTotal, AbuseIPDB, OTX, urlscan.io, NIST NVD, OSV.dev, npm/PyPI registries)
3. Compute a weighted composite threat score (0.0–1.0)
4. Map to one of 5 severity verdicts: **CLEAN → LOW → MEDIUM → HIGH → CRITICAL**
5. Generate a structured threat report with recommended actions
6. Stream a full execution trace via OpenTelemetry (OTLP/HTTP) to the configured collector for observability

## Quick Start

FlowRun runs as a container image with a small web UI on **port 7777**. Works identically with Docker or Podman — no Python or local dependency install required.

### 1. Prepare credentials
```bash
cp .env.template .env   # then fill in the 5 required API keys
```

### 2. Start the stack

**Wrapper script (auto-detects Docker/Podman):**
```bash
./scripts/compose.sh up -d --build
```

**Native Docker Compose:**
```bash
docker compose up -d --build
```

**Native Podman Compose:**
```bash
podman compose up -d --build
```

All commands build the image on first run and start the agent. Open <http://localhost:7777>.

### 3. Use the UI
Paste any IOC (IP, domain, URL, file hash, CVE, package) into the input field and click **Triage**. The full threat report renders inline below the form.

### 4. Stop the stack
```bash
./scripts/compose.sh down
# or native commands:
# docker compose down
# podman compose down
```

### Demo mode
Set `FLOWRUN_DEMO_MODE=true` to serve `POST /api/v1/triage` from local fixtures only — no API keys, no live calls:
```bash
FLOWRUN_DEMO_MODE=true docker compose up -d --build
# or: FLOWRUN_DEMO_MODE=true podman compose up -d --build
```
See the [Postman demo runbook](demo/POSTMAN_DEMO_INSTRUCTIONS.md) for the full walkthrough.

### Tracing
By default the container ships OpenTelemetry spans to `http://host.docker.internal:4318` — your host machine's local OTLP/HTTP collector port. If no collector is running, tracing fails silently and triage continues normally. To target a different endpoint, set `OTEL_EXPORTER_OTLP_ENDPOINT` in your `.env`.

See [QUICK_START.md](QUICK_START.md) for the full setup walkthrough.

## Postman demo checks (local + CI parity)

A CI workflow runs `postman_collection.json` in **demo mode** and uploads:
- Newman CLI summary
- JUnit XML
- JSON run report

To reproduce locally, follow [`demo/POSTMAN_DEMO_INSTRUCTIONS.md`](demo/POSTMAN_DEMO_INSTRUCTIONS.md).

Minimum pass criteria:
- All requests pass (Newman exit code `0`).
- No failed assertions.
- Health endpoint latency is below threshold when the latency check is enabled.

## Documentation

| Document | Description |
|----------|-------------|
| [QUICK_START.md](QUICK_START.md) | Setup, installation, and first-run guide |
| [FlowRun_Streamlet_IoC_Triage_User_Manual_v2.3.md](docs/FlowRun_Streamlet_IoC_Triage_User_Manual_v2.md) | Full user manual with usage instructions |
| [FlowRun_Streamlet_IoC_Triage_PRD_v2.md](docs/FlowRun_Streamlet_IoC_Triage_PRD_v2.md) | Product requirements (FR-01–FR-39, NFR-01–NFR-10) |
| [FlowRun_Streamlet_IoC_Triage_Architecture_v2.md](docs/FlowRun_Streamlet_IoC_Triage_Architecture_v2.md) | System architecture and component design |
| [FlowRun_Streamlet_Build_Prompt.md](docs/FlowRun_Streamlet_Build_Prompt.md) | Original engineering build instructions |
| [API.md](docs/API.md) | HTTP API reference — endpoints, schemas, error codes, execution modes |
| [POSTMAN_SETUP.md](demo/POSTMAN_SETUP.md) | First-time Postman setup — install, import, send first request, wire up CI |
| [POSTMAN_DEMO_INSTRUCTIONS.md](demo/POSTMAN_DEMO_INSTRUCTIONS.md) | Postman demo runbook — click-and-type setup and steps |
| [POSTMAN_DEMO_SCRIPT.md](demo/POSTMAN_DEMO_SCRIPT.md) | Presenter script for the live Postman demo |

## Project Structure

```
flowrun-streamlet-ioc-triage-v0.0.33/
├── compose.yaml              # Docker / Podman compose (default deployment)
├── Dockerfile                # Container image — uvicorn on port 7777
├── .dockerignore
├── flowrun_agent.py          # CLI entry point
├── flowrun_agent.ipynb       # Jupyter Notebook (8 cells)
├── requirements.txt
├── .env.template             # API key template (no values)
├── .gitignore
├── QUICK_START.md
├── README.md
├── web/
│   ├── app.py                # FastAPI app — /, /triage, /health
│   ├── templates/index.html  # htmx-driven UI on port 7777
│   └── static/style.css
├── agent/
│   ├── graph.py              # LangGraph StateGraph — nodes & edges
│   ├── state.py              # AgentState TypedDict
│   ├── llm.py                # Model config (single file to change models)
│   ├── scoring.py            # Weighted scoring formula & severity mapping
│   ├── report.py             # CLI text & HTML report formatters
│   ├── credentials.py        # .env → os.environ → getpass() resolution
│   ├── tracing.py            # OpenTelemetry / Traceloop (OpenLLMetry) setup
│   ├── tools/                # LangChain tool wrappers
│   └── integrations/         # Raw HTTP clients & response parsers
├── tests/                    # pytest suite (164+ tests)
└── docs/                     # PRD, Architecture, User Manual, Build Prompt, ERD
```

## Changing Models

All model configuration lives in `agent/llm.py`. To swap models, edit `MODEL_CONFIG`:

```python
MODEL_CONFIG = {
    "classifier": {"model": "gpt-4o-mini", "temperature": 0.0},
    "report":     {"model": "gpt-4o",      "temperature": 0.3},
}
```

No other file needs to change.

## Changelog

**v0.0.33 — Containerized default deployment + web UI**
- **New**: `Dockerfile` and `compose.yaml` make the container the default install path. Single command (`docker compose up` or `podman compose up`) builds and starts the stack.
- **New**: FastAPI web UI on port **7777** (`web/app.py`) with an htmx-driven form. Reuses the existing LangGraph and the HTML report formatter — no agent logic changed.
- **New**: `/health` endpoint for container liveness probes; built-in `HEALTHCHECK` on the image.
- **New**: `FLOWRUN_NO_PROMPT=1` skips `getpass()` so the agent fails fast in non-interactive environments instead of hanging.
- **New**: Default OTLP destination inside the container is `http://host.docker.internal:4318`, made reachable on both Docker Desktop and rootless Podman via `extra_hosts: host-gateway`.
- **Compatible**: CLI (`python flowrun_agent.py`) and the Jupyter notebook continue to work unchanged.

**v0.0.32 — Vendor-neutral tracing**
- **Removed**: Arize-specific tracing dependencies (`arize-otel`, `openinference-instrumentation-langchain`)
- **Added**: Standard OpenTelemetry SDK + Traceloop SDK (OpenLLMetry). Auto-instruments LangChain, LangGraph, and OpenAI.
- **Default destination**: local OTLP/HTTP collector agent on `http://localhost:4318`. Override via `OTEL_EXPORTER_OTLP_ENDPOINT` to ship to any collector or managed observability backend.
- **Required keys reduced from 7 to 5**: `ARIZE_API_KEY` and `ARIZE_SPACE_ID` are gone. OpenTelemetry configuration is fully optional.
- **CLI report footer** now shows the active `OTLP ENDPOINT` instead of an Arize trace URL.

**v0.0.31 — Package supply chain analysis + multi-ecosystem scanning**
- **New IOC type**: `package` — supports `ecosystem:name` format (e.g., `npm:postmark-mcp`, `pypi:requessts`, `rhel:openssl`, `debian:nginx`)
- **New IOC type**: `package_multi` — bare package names (e.g., `traceroute`, `express`) are automatically scanned across all 10 major language ecosystems simultaneously
- **New data source**: OSV.dev (Google) — scans for known malicious packages (MAL advisories) and vulnerabilities. No API key needed.
- **New data source**: Package registry metadata (npm/PyPI) — fetches creation date, maintainer count, install scripts, source repo presence. No API key needed.
- **27 supported ecosystems**: npm, PyPI, crates.io, Go, Maven, NuGet, RubyGems, Packagist, Pub, Hex, CocoaPods, Hackage, CRAN, SwiftURL, Red Hat, Debian, Ubuntu, Alpine, Rocky Linux, AlmaLinux, SUSE, Android, Linux (kernel), Bitnami, curl (with aliases like `pip:`, `cargo:`, `gem:`, `redhat:`)
- **Per-ecosystem breakdown**: Multi-scan reports show results for each ecosystem individually, highlighting which ones have advisories
- **New weight sets**: `PACKAGE_WEIGHTS` (OSV 60%, Registry 40%), `PACKAGE_MULTI_WEIGHTS` (OSV multi 100%)
- **Updated**: All documentation (PRD, Architecture, User Manual, Build Prompt, Addendum)

**v0.0.26 — Enhanced report intelligence**
- **New**: Per-engine AV detection names for hash IOCs (e.g., "Kaspersky: Trojan.Win32.Agent")
- **New**: OTX threat actor and campaign tag extraction shown in findings
- **New**: CVSS severity string and attack vector for CVE reports (e.g., "CVSS: 9.8 (CRITICAL), Vector: NETWORK")
- **New**: Conflicting signal callout — highlighted warning when sources disagree (e.g., VT clean but OTX shows APT pulses)
- **New**: TL;DR one-line summary at the top of every report
- **New**: Timestamp on every report
- **New**: Data confidence indicator when sources are missing

**v0.0.24 — URL→domain dual-query enrichment**
- **New**: When a URL is submitted, the domain is automatically extracted and queried separately against VirusTotal and OTX in addition to the URL-level queries. For each source, the response with the stronger threat signal is kept. This catches cases where a domain has known-bad reputation even if the specific URL path is new.
- **New**: Domains are now also sent to urlscan.io for live browser analysis (prepended with `https://`).

**v0.0.21 — Scoring sensitivity fix**
- **Fixed**: VirusTotal normalizer now uses a non-linear detection-count curve instead of a linear ratio. Even a few malicious detections (e.g. 13/94 engines) now correctly produce a MEDIUM or higher score, matching real-world analyst expectations.

**v0.2 — Runtime compatibility fixes**
- **Fixed**: Tracing init now uses `project_name` correctly (was `model_id`)
- **Fixed**: Domain IOCs (e.g. `malware.wicar.org`) now classified by regex — no LLM fallback needed
- **Fixed**: Model config uses real, available models (`gpt-4o-mini`, `gpt-4o`) instead of unreleased GPT-5.2
- **Added**: Jupyter kernel setup instructions (ipykernel registration for venv users)
- **Added**: All documentation bundled in `docs/` folder
- **Added**: Quick Start guide with troubleshooting table
- **Updated**: Notebook includes kernel selection guidance and test IOC suggestions


## API Execution Mode Precedence

The API has deterministic execution priority:

1. `FLOWRUN_DEMO_MODE=true` → `/api/v1/triage` resolves fixtures only by IOC type + canonical IOC key (then optional type default), and raises an explicit missing-fixture error if unresolved.
2. `/api/v1/triage/mock` → returns a canned mock fixture only (`fixtures/demo/mock.json`).
3. Live mode (default) → `/api/v1/triage` runs real integrations.

Responses include `execution_mode` (`demo`, `mock`, or `live`) and `fixture_id` when a fixture is used, so Postman assertions can validate mode selection deterministically.

For the full endpoint, schema, and error-code reference, see [`docs/API.md`](docs/API.md).
