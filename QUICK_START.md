# Ross Moda IoC Triage Agent — Quick Start Guide

Ross Moda ships as a container image with a small web UI on **port 7777**.
Everything below works identically with **Docker** or **Podman** — pick one.

## 1. Prerequisites

| Engine | Minimum version | Compose support |
|--------|-----------------|-----------------|
| Docker | 20.10+          | `docker compose` (Compose v2) |
| Podman | 4.0+            | `podman compose` |

No Python, virtualenv, or local dependency install is required — the image
bundles everything.

## 2. Extract and enter the project

```bash
tar xzf ross-moda-ioc-triage-agent.tar.gz
cd ross-moda-ioc-triage-agent
```

## 3. Set up your API keys

Copy the template and fill in your keys:

```bash
cp .env.template .env
```

Open `.env` in any text editor and paste each key directly after the `=` sign — no quotes, no spaces:

```
OPENAI_API_KEY=sk-your-openai-key-here
VIRUSTOTAL_API_KEY=your-vt-key-here
ABUSEIPDB_API_KEY=your-abuseipdb-key-here
OTX_API_KEY=your-otx-key-here
URLSCAN_API_KEY=your-urlscan-key-here
```

`.env` is optional — the container still starts without it — but live triage
needs all five keys. (Demo mode, see Step 6, needs none.)

### Where to get your API keys

| Key | Where to find it |
|-----|-----------------|
| OPENAI_API_KEY | [platform.openai.com → API Keys](https://platform.openai.com/api-keys) |
| VIRUSTOTAL_API_KEY | [virustotal.com → Profile → API Key](https://www.virustotal.com) |
| ABUSEIPDB_API_KEY | [abuseipdb.com → Account → API](https://www.abuseipdb.com) |
| OTX_API_KEY | [otx.alienvault.com → Settings → API Key](https://otx.alienvault.com) |
| URLSCAN_API_KEY | [urlscan.io → Settings → API Keys](https://urlscan.io) |

## 4. Start the stack

The image builds from the local `Dockerfile` on the first run and is reused
afterward. Pick whichever command matches your engine:

```bash
# Wrapper script — auto-detects Docker or Podman
./scripts/compose.sh up --build -d

# Native Docker Compose
docker compose up --build -d

# Native Podman Compose
podman compose up --build -d
```

Then open <http://localhost:7777>.

## 5. Use the web UI

Paste any IOC into the input field and click **Triage**. The agent classifies
the IOC, queries the threat-intelligence sources, and renders the full report
inline below the form.

Supported IOC types — IP, domain, URL, file hash (MD5/SHA-1/SHA-256), CVE
identifier, or software package.

Example package IOC:
```
npm:postmark-mcp
```

## 6. Run the Postman demo (optional)

Demo mode serves `POST /api/v1/triage` from local fixtures only — no API keys,
no live calls. Start the stack with `IOC_TRIAGE_DEMO_MODE=true`:

```bash
IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
# Podman:  IOC_TRIAGE_DEMO_MODE=true podman compose up --build -d
# Wrapper: IOC_TRIAGE_DEMO_MODE=true ./scripts/compose.sh up --build -d
```

The full demo runbook lives in [`demo/POSTMAN_DEMO_INSTRUCTIONS.md`](demo/POSTMAN_DEMO_INSTRUCTIONS.md).

## 7. Stop the stack

```bash
./scripts/compose.sh down
# or native commands:
# docker compose down
# podman compose down
```

## 8. Tracing (optional)

By default the container ships OpenTelemetry spans via OTLP/HTTP to
`http://host.docker.internal:4318` — your host machine's local OpenTelemetry
collector port. If no collector is running, tracing fails silently and triage
continues normally.

To send traces somewhere else, set `OTEL_EXPORTER_OTLP_ENDPOINT` (and optionally
`OTEL_EXPORTER_OTLP_HEADERS` for authenticated backends) in your `.env`:

```
# OTEL_EXPORTER_OTLP_ENDPOINT=http://host.docker.internal:4318
# OTEL_EXPORTER_OTLP_HEADERS=Authorization=Bearer your_token
# OTEL_SERVICE_NAME=ross-moda-ioc-triage-agent
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `neither 'docker' nor 'podman' was found` (wrapper) | Install Docker 20.10+ or Podman 4.0+, or set `CONTAINER_ENGINE` to the engine you want |
| Port 7777 already in use | Stop the other process, or edit the `ports:` mapping in `compose.yaml` |
| `Required API keys not provided` in logs | One or more keys missing from `.env` — check the list in Step 3, no quotes, no trailing spaces |
| Triage requests fail but the UI loads | The container started without valid keys — fix `.env` and re-run `compose ... up --build -d` |
| Want to inspect logs | `./scripts/compose.sh logs -f` (or `docker compose logs -f` / `podman compose logs -f`) |
| Rebuild from scratch | `./scripts/compose.sh down` then `./scripts/compose.sh up --build -d` |
