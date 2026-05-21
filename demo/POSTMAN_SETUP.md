# Postman Setup — First-Time Guide

First-time setup guide for the FlowRun IoC Triage Postman collection. It
takes a Postman first-timer from zero install to a green CI run on GitHub.

## What this file is

This is the entry-level setup doc. It assumes Postman has never been opened.
Two sibling docs assume setup is already done: [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md)
is the click-and-type runbook for delivering the live demo, and
[`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md) is the presenter narration
for the deck. Start here, finish with a green run, then move to those.

Postman is a desktop client for building and running HTTP requests against an
API. This repo ships a Postman collection that exercises the FlowRun IoC
Triage API and asserts on every response.

## Prerequisites

- Docker 20.10+ or Podman 4.0+. Every `docker compose` command below works
  identically with `podman compose` — substitute it as a drop-in.
- A GitHub account — only required for the CI section (steps 10–12).
- node + npm — only required to run Newman locally via the
  `scripts/postman.sh` wrapper (step 9).

## Install Postman

Download the desktop app from <https://www.postman.com/downloads/> and install
it. The free tier covers everything in this repo — no paid features required.

## Start the API locally in demo mode

Run from the repo root. Demo mode serves every response from local fixtures
baked into the image — no `.env` file and no API keys needed.

```bash
FLOWRUN_DEMO_MODE=true docker compose up --build -d
curl http://127.0.0.1:7777/health
```

The `curl` returns `{"status":"ok",...}` when the API is up. The container
must stay running for the rest of this guide.

## Import the collection and environments

Three files live in the repo root:

- `postman_collection.json`
- `postman_environment.demo.json`
- `postman_environment.local.json`

In Postman, click **Import** (top-left). Drag all three files into the import
dialog and confirm. The collection **FlowRun IoC Triage API** appears under
**Collections** in the left nav; both environments appear under
**Environments**.

## Activate the Demo environment

Open the environment dropdown (top-right) and select
**FlowRun IoC Triage — Demo**.

The Demo environment supplies `baseUrl`, `iocType`, and
`expectedExecutionMode=demo`. The collection's assertions read these values —
they need to know the demo mode is expected in order to check for it.

Suggested values: 
baseUrl=localhost:7777
iocType=8.8.8.8
expectedExecutionMode=demo


## Send the first request

1. In the left nav, expand the collection and open folder **00 — Liveness**.
2. Click request **GET /health**.
3. Click **Send**.
4. Open the **Test Results** tab in the response pane.

A passing request shows green checkmarks, one per assertion, each labelled
`PASS`. The most common failure is a red **connection refused** error — that
means the container is not running. Re-check the previous step.

## Run the full collection

1. Click the collection name **FlowRun IoC Triage API** in the left nav.
2. Click **Run** to open the Collection Runner.
3. Confirm the environment selector in the Runner reads **Demo**.
4. Click **Run FlowRun IoC Triage API**.

Expected outcome: 37 green assertions in roughly one second.

## Reproduce CI locally with Newman (optional)

Newman is the headless engine that Postman's Collection Runner uses under the
hood. The `scripts/postman.sh` wrapper drives it, and CI runs the same script —
so a pass locally means a pass in CI.

```bash
npm install -g newman newman-reporter-junitfull newman-reporter-htmlextra
./scripts/postman.sh smoke   # quick subset
./scripts/postman.sh full    # everything + artifacts
```

`smoke` runs the Liveness and Examples folders only. `full` runs every folder
and writes artifacts to `artifacts/postman/`.

## CI on GitHub — what's already there

The workflow `.github/workflows/postman.yml` runs on every push and pull
request. It:

- Boots the API in demo mode (`FLOWRUN_DEMO_MODE=true`).
- Polls `/health` until the server is ready.
- Runs `scripts/postman.sh full`.
- Gates on the total assertion count and zero failures via `jq`.
- Uploads the Newman CLI summary, JUnit XML, JSON, and HTML reports as
  artifacts with `if: always()`, so reports are available even on failure.

No additional setup is required. Commit and push, then open the **Actions**
tab on GitHub to watch the `postman-demo` job run.

## Block bad PRs from merging

Require the CI check to pass before any PR can merge:

1. Go to repo **Settings** → **Branches** → **Add branch ruleset** (or
   **Add rule** on the legacy branch-protection UI).
2. Set the branch name pattern to `main` (or the repo's default branch).
3. Enable **Require status checks to pass before merging**.
4. Search for and select the `postman-demo` check.
5. Click **Save**.

Any PR that breaks an assertion now blocks merge unless an admin overrides.

## Sync Postman ↔ GitHub (optional)

Postman's native GitHub integration syncs the collection back to the repo when
it is edited in the Postman UI.

1. Open **Workspace** (top-left) → **Settings** → **Integrations**.
2. Select **GitHub** → **Add Integration**.
3. Authenticate with GitHub.
4. Pick the repo, branch, collection, and file path (`postman_collection.json`).
5. Choose the sync direction.

Without the integration, the workflow to update the collection is: **Export**
from Postman → overwrite `postman_collection.json` → commit. With the
integration, the sync is automatic.

## Switching to live mode (optional)

With `.env` populated with real API keys, swap the environment dropdown to
**FlowRun IoC Triage — Local**. That environment sets
`expectedExecutionMode=live`. The schema assertions still pass; the
mode-precedence assertions now verify the agent made real upstream calls
instead of serving fixtures.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `ECONNREFUSED` on every request | Container not running — re-run the demo-mode start command. |
| All requests return `503 DEMO_FIXTURE_MISSING` | Container started without `FLOWRUN_DEMO_MODE=true` — restart with the variable set. |
| `expectedExecutionMode` assertion fails | Wrong environment selected — pick **FlowRun IoC Triage — Demo** in the dropdown. |
| CI passes locally but fails on GitHub | Open the `newman-report.html` artifact in the failing Actions run for the per-assertion detail. |
| Postman won't import the collection | Verify the JSON is valid: `jq . postman_collection.json`. |

## Where to go next

- Live demo runbook: [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md)
- Presenter narration: [`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md)
- API reference: [`../docs/API.md`](../docs/API.md)
