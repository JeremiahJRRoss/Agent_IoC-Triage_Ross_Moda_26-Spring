# Postman Setup — First-Time Guide

## What this file is

This is the first-time setup guide for the FlowRun IoC Triage Postman
collection. Postman is an HTTP client for building and running requests
against an API; this repo ships a collection that exercises the FlowRun IoC
Triage API and asserts on every response. This guide takes a developer who
has never opened Postman from zero install to a green collection run, then
on to CI on GitHub. Two sibling docs assume setup is already done:
[`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md) is the
click-and-type runbook for delivering the live demo, and
[`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md) is the presenter
narration for the deck. Start here; move to those once you have a green run.

## Pick your track

Decide how you will reach the API before installing anything. The choice
determines which Postman client you need. Both tracks share the import and
environment steps, but diverge on the client and on where the container runs.

| Track | When to pick it | Postman client needed |
|---|---|---|
| **A — Local** | Container on your machine, `127.0.0.1:7777` | Desktop app, or web + Desktop Agent |
| **B — Public** | Container behind a tunnel or deployed URL | Any (desktop, web, or web + Cloud Agent) |

Track A is the default — pick it if you are iterating on the code, running
CI locally, or just learning the collection. Pick Track B if you want to
share the demo, run tests from a different network, or hand a URL to a
colleague.

The localhost trap is the reason the client choice matters:

> Postman's web app runs in `guiderun.postman.co`. Requests from the
> browser to `http://127.0.0.1` are sent by *Postman's cloud servers*,
> which have no route to your laptop. You need either the desktop app or a
> local agent process to bridge the gap. Track A covers both options.

## Prerequisites (shared)

- Docker 20.10+ or Podman 4.0+. Every `docker compose` command below works
  identically with `podman compose` — substitute it as a drop-in.
- A GitHub account — only required for the CI section.
- Node + npm — only required to run Newman locally via the
  `scripts/postman.sh` wrapper (Track A only).

## Install Postman

### Track A — Local: pick desktop or web + agent

A pure web-only path does not work for Track A — the web app's Cloud Agent
cannot reach `localhost`. Pick one of the two options below.

**Desktop app (recommended)**

Download the desktop app from <https://www.postman.com/downloads/>, install
it, and sign in. It talks to `localhost` natively — no agent needed. This
is what most developers use.

**Web app + Desktop Agent**

To stay in the browser:

1. Open Postman web at <https://web.postman.co> (or `guiderun.postman.co`).
2. Look at the **bottom status bar** of the Postman window — find the agent
   selector, which reads **Cloud Agent** by default.
3. Switch it to **Desktop Agent** — the dropdown offers a download link if
   the agent is not installed.
4. After install, the selector shows **Desktop Agent** and requests to
   `localhost` work.

The Desktop Agent is a tiny background process that runs in your system
tray / menu bar. The web app's UI is unchanged; only request routing changes.

### Track B — Public: any client works

Any Postman client works for Track B, because the public URL is reachable
from anywhere — desktop app, web app, or web + Cloud Agent. The desktop app
is still recommended for general use, but if you prefer the web app, no
agent install is needed for this track.

## Start the API

### Track A — Local

Run from the repo root. Demo mode serves every response from local fixtures
baked into the image — no `.env` file and no API keys needed.

```bash
FLOWRUN_DEMO_MODE=true docker compose up --build -d
curl http://127.0.0.1:7777/health
```

The `curl` returns `{"status":"ok",...}` when the API is up. The container
must stay running for the rest of this guide.

### Track B — Public

You need a public URL that resolves to a container running the same image.
There are two ways to get one.

**Tunnel a local container with ngrok**

```bash
# Terminal 1 — start the container
FLOWRUN_DEMO_MODE=true docker compose up --build -d

# Terminal 2 — tunnel it
ngrok http 7777
```

ngrok prints a URL like `https://abc123.ngrok.app`. Note it down — it
replaces `127.0.0.1:7777` in the environment file. (`cloudflared` is a
drop-in alternative to ngrok; its setup is not covered here.)

> Anyone with the tunnel URL can hit your container while the tunnel is
> open. Demo mode is safe — fixtures only, no keys. **Do not tunnel live
> mode.** API keys are inside the container and live triage calls will burn
> against your accounts.

**Deploy the container to a cloud provider**

The `Dockerfile` and `compose.yaml` in the repo root are OCI-compatible and
run as-is on any standard host — Fly.io, Render, Railway, AWS App Runner,
Google Cloud Run, and similar. Provide the `.env` (or the provider's
equivalent secrets layer) at the deployment provider. The public URL the
provider returns becomes the new `baseUrl`.

This guide does not cover provider-specific deployment — that lives in each
provider's own docs. Once the container is deployed and reachable, return
here and continue.

## Import the collection and environments (shared)

Three files live in the repo root:

- `postman_collection.json`
- `postman_environment.demo.json`
- `postman_environment.local.json`

The **Import** control sits in a different place depending on the client:

- **Desktop app**: top-left, a dedicated **Import** button next to
  **Collections**.
- **Web app**: top-left under the workspace-name dropdown, or via the
  keyboard shortcut `⌘+O` (Mac) / `Ctrl+O` (Windows/Linux).

Open the import dialog, drag all three files into it, and confirm. The
collection **FlowRun IoC Triage API** appears under **Collections** in the
left nav; both environments appear under **Environments**.

## Configure the environment for your track

### Track A — Local

Open the environment dropdown (top-right) and select **FlowRun IoC Triage —
Demo**. No changes needed — `baseUrl` is already `http://127.0.0.1:7777`.

### Track B — Public

1. Open the environment dropdown (top-right) and select **FlowRun IoC
   Triage — Demo**.
2. Open the environment for editing: left sidebar → **Environments** →
   click the environment name → click the pencil / edit icon.
3. Change `baseUrl` from `http://127.0.0.1:7777` to your public URL — the
   ngrok URL or the deployment URL, with no trailing slash.
4. Save with `⌘+S` / `Ctrl+S`.

Do not edit `expectedExecutionMode` — keep it as `demo`. The container
behind the URL determines the mode, not the client.

## Send your first request (shared)

1. In the left nav, expand the collection and open folder **00 — Liveness**.
2. Click request **GET /health**.
3. Click **Send**.
4. Open the **Test Results** tab in the response pane.

A passing request shows a row of green checkmarks, one per assertion, each
labelled `PASS`. The two most common failures:

- `Error: connect ECONNREFUSED` (Track A) — the container is not running,
  or the web app's agent is not switched to **Desktop Agent**.
- `Error: getaddrinfo ENOTFOUND` (Track B) — the tunnel is closed, or the
  public URL is wrong (typo, missing `https://` scheme, or trailing slash).

## Run the full collection (shared)

1. Click the collection name **FlowRun IoC Triage API** in the left nav.
2. Click **Run** to open the Collection Runner.
3. Confirm the Runner's environment selector reads **Demo**.
4. Click **Run FlowRun IoC Triage API**.

Expected: 37 green assertions in about a second on Track A — slightly
slower on Track B because each request makes a network round-trip over the
tunnel or to the deployment.

## Reproduce CI locally with Newman (optional, Track A only)

Skip this section if you picked Track B. Newman runs against
`127.0.0.1:7777` from the shell, so it is Track A territory.

Newman is the headless engine that Postman's Collection Runner uses under
the hood. The `scripts/postman.sh` wrapper drives it, and CI runs the same
script — a pass locally means a pass in CI.

```bash
npm install -g newman newman-reporter-junitfull newman-reporter-htmlextra
./scripts/postman.sh smoke   # quick subset
./scripts/postman.sh full    # everything + artifacts
```

`smoke` runs the Liveness and Examples folders only. `full` runs every
folder and writes artifacts to `artifacts/postman/`.

## CI on GitHub — what's already there (shared)

The workflow `.github/workflows/postman.yml` runs on every push and pull
request. It:

- Boots the API in demo mode — a bare `uvicorn` process with
  `FLOWRUN_DEMO_MODE=true`, started inside the runner (it does not use a
  container).
- Polls `/health` until the server is ready.
- Fails the build if `/health` latency exceeds `HEALTH_LATENCY_THRESHOLD_MS`
  (1000ms by default).
- Runs `scripts/postman.sh full`.
- Gates on the total assertion count (`>= 25`) and zero failures via `jq`.
- Uploads the Newman CLI summary, JUnit XML, JSON, and HTML reports plus
  `server.log` as artifacts with `if: always()`, so reports exist even when
  the run fails.

No extra setup is required. The workflow is not something you configure in
GitHub — the YAML file in the repo *is* the configuration. GitHub Actions
runs any workflow file it finds under `.github/workflows/` automatically.
Commit and push, then open the **Actions** tab on GitHub to watch the
`postman-demo` job run.

CI is Track A by nature — it runs the API inside the runner. Retargeting CI
at a Track B public URL is not a one-line change: the workflow's `BASE_URL`
variable only governs the health-poll and latency-check steps, while the
Newman run reads `baseUrl` from `postman_environment.demo.json`. To point
the test itself at a public URL, edit that file's `baseUrl` (or pass
`newman --env-var "baseUrl=<url>"`). The in-runner default is preferred
anyway — it does not depend on external uptime.

## Block bad PRs from merging (shared)

Require the CI check to pass before any PR can merge:

1. Go to repo **Settings** → **Branches** → **Add branch ruleset**.
2. Set the branch name pattern to `main`.
3. Enable **Require status checks to pass before merging**.
4. Search for and select the `postman-demo` check.
5. Click **Save**.

PRs that break an assertion now block merge unless an admin overrides.

## Sync Postman ↔ GitHub (optional, shared)

Postman's native GitHub integration syncs the collection back to the repo
when it is edited in the Postman UI:

1. Open **Workspace** (top-left) → **Settings** → **Integrations**.
2. Select **GitHub** → **Add Integration**.
3. Authenticate with GitHub.
4. Pick the repo, branch, collection, and file path
   (`postman_collection.json`).
5. Choose the sync direction.

Without the integration, the workflow to update the collection is
**Export** from Postman → overwrite `postman_collection.json` → commit.
With the integration, the sync is automatic.

## Switching to live mode (optional, both tracks)

With `.env` populated with real API keys, swap the environment dropdown to
**FlowRun IoC Triage — Local**, which sets `expectedExecutionMode=live`.
Schema assertions still pass — the response shape does not change between
modes — and the mode-precedence assertions now verify the agent made real
upstream calls instead of serving fixtures.

The `CVE — fixture miss` test in folder **02 — Triage (demo mode)** only
passes in demo mode: it asserts `503 DEMO_FIXTURE_MISSING`. In live mode
that request hits NVD and returns a real verdict, so the negative-path test
"fails" by design.

> If you tunnel a container running in live mode through ngrok, the
> container is publicly reachable and will burn API quota on every request
> anyone sends. Add authentication at the tunnel layer, or use Track B only
> for demo-mode deployments.

## Troubleshooting

| Symptom | Track | Fix |
|---|---|---|
| `Error: connect ECONNREFUSED` | A | Container not running, or web app agent not switched to **Desktop Agent**. |
| `getaddrinfo ENOTFOUND` / `EAI_AGAIN` | B | Tunnel closed, or DNS for the deployment failed — restart the tunnel or check the host. |
| All requests return `503 DEMO_FIXTURE_MISSING` | A & B | Container started without `FLOWRUN_DEMO_MODE=true` — restart with the variable set. |
| Web app sends to `localhost` but nothing happens | A | Bottom-bar agent selector is still on **Cloud Agent** — switch it to **Desktop Agent**. |
| `expectedExecutionMode` assertion fails | A & B | Wrong environment selected, or `baseUrl` does not match where the container actually runs. |
| CI passes locally but fails on GitHub | A | Open the `newman-report.html` artifact in the failing Actions run for per-assertion detail. |
| Postman won't import the collection | A & B | Verify the JSON is valid: `jq . postman_collection.json`. |
| ngrok URL works in a browser but Postman returns "Tunnel expired/replaced" | B | Free ngrok URLs rotate per session — restart ngrok and update `baseUrl`. |

## Where to go next

- Live demo runbook: [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md)
- Presenter narration: [`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md)
- API reference: [`../docs/API.md`](../docs/API.md)
