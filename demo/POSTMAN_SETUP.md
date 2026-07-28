# Postman Setup — A First-Time Guide

Most API test suites drift. You write them on a Friday, the service changes on a Monday, and by Wednesday no one remembers whether the suite still reflects what the code actually does. The setup you are about to do is engineered against that drift. The collection reads its schema from the running server on every execution, so a test cannot quietly disagree with the contract — if the schema moves, the assertion moves with it, or the build turns red.

This guide takes you from a clean machine to a green run, locally and in CI. It covers five things:

1. Launching the service in a container.
2. Importing the collection into Postman on the web.
3. Running the tests in the Postman app.
4. Watching the same tests run in GitHub Actions.
5. Reproducing the CI run on your own machine with Newman and the GitHub CLI.

You will finish in roughly fifteen minutes, with a working loop you can hand to a teammate.

Prerequisites are small:

- **Docker 20.10 or newer** (Compose v2 is bundled).
- **A Postman account** (the free tier is enough).
- **Node.js 20 and the GitHub CLI (`gh`)** — only needed for the CLI section at the end.

Everything else is in the repository.

---

## The 60-second mental model

Three ideas anchor the rest of this document. Skim them once; they pay back the time.

**The service has three execution modes, and the server decides which one to use.**
The collection works against `live`, `demo`, and `mock`.

- **Live mode** calls the real threat-intelligence APIs (VirusTotal, AbuseIPDB, OTX, urlscan.io, NVD, OSV.dev) and needs API keys.
- **Demo mode** reads canned responses from `fixtures/demo/*.json` and needs no keys at all.
- **Mock mode** is a single canned payload used for schema-only checks.

Precedence is strict and lives in exactly one function (`web/app.py::triage_api`): if `IOC_TRIAGE_DEMO_MODE=true` is set, demo mode wins, and a missing fixture is a hard `503 DEMO_FIXTURE_MISSING` — never a silent fallback to live. This is the test you can rely on: demo cannot quietly become live.

**The collection is a JSON file that runs identically in Postman, in Newman, and in GitHub Actions.**
Postman's desktop app and Newman — its headless CLI sibling — share the same JavaScript sandbox.

- The collection you import from `postman_collection.json` is the same file CI consumes.
- There is no separate "test code" in another language to keep in sync.
- A green run in Postman is a green run in CI is a green run on a teammate's laptop.

**The schema isn't hard-coded.**
When the collection runs, the sequence is:

1. The collection's first request fetches `/openapi.json` from the running server — before any assertion fires.
2. FastAPI auto-generates that document from the Pydantic models in `web/schemas.py`.
3. The collection caches the `components.schemas` block in a variable.
4. Every contract assertion validates against the cached block with AJV (a JSON Schema validator).

When a developer changes a Pydantic model, the OpenAPI document changes on the next server restart, and the next collection run picks it up automatically. The tests cannot drift from the contract.

---

## 1. Launch the container

The repository ships a `Dockerfile` and a `compose.yaml`. Both target a single service on port `7777`. The image bundles:

- Python 3.11
- The pinned dependency tree from `requirements.lock`
- The application code

There is nothing to install on the host except Docker itself.

From the repository root:

```bash
IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
```

Three things are happening in that one line:

- **`--build`** tells Compose to build the image from the local `Dockerfile` the first time you run it, then reuse the cached image afterward.
- **`-d`** detaches the container so you get your shell back.
- **`IOC_TRIAGE_DEMO_MODE=true`** is read by `compose.yaml` and injected into the container's environment, which the FastAPI app checks at startup. With demo mode on, the app skips credential resolution entirely — it does not look for a `.env` file, does not call `getpass()`, and does not fail when API keys are absent. This is what makes the demo runnable on a clean machine.

Confirm the service is up:

```bash
curl http://127.0.0.1:7777/health
```

A successful response looks like `{"status":"ok","trace_endpoint":"http://localhost:4318"}`. The `/health` endpoint does no agent work — it touches no LangGraph node, makes no outbound calls. It exists so orchestrators (and your shell) can ask the cheapest possible question: are you listening? The `trace_endpoint` field reports the OpenTelemetry destination the server resolved at startup; if you have no collector running, it still reports the default, and triage continues without tracing.

Leave the container running for the rest of this guide. To stop it later:

```bash
docker compose down
```

---

## 2. Set up Postman in the web UI

Postman runs in two places that share state through Postman's cloud:

- **The desktop app**, which is what most engineers use day-to-day.
- **The web client at `go.postman.co`**, which is identical in feature set but easier for first-time setup because there is nothing to install.

Both write to the same workspace. Use the web client to import, then use either to run.

Sign in at [go.postman.co](https://go.postman.co). Postman drops you into your default workspace. Three files in the repository root need to land here:

- **`postman_collection.json`** — the collection itself: 5 folders, 11 requests, 37 assertions.
- **`postman_environment.demo.json`** — values for running against the demo-mode server.
- **`postman_environment.local.json`** — values for running against a live-mode server.

Click **Import** in the upper left. Drag all three files into the dialog. Postman parses them, distinguishes the collection from the environments (collections describe requests; environments describe values to substitute into those requests), and places them in the correct sidebar sections:

- The collection appears under **Collections** as *Ross Moda IoC Triage API*.
- The two environment files appear under **Environments**.

The distinction between *collection variables* and *environment variables* matters here. Both can be referenced as `{{baseUrl}}` inside a request, and either can supply a value:

- **Collection variables** travel with the collection — anyone who imports the file gets them.
- **Environment variables** are a separate, swappable layer on top: select a different environment from the dropdown in the upper right, and every request reads from the new set without you editing a single request.

Three variables are environment-level on purpose:

- **`baseUrl`** — where the server lives.
- **`iocType`** — which example payload to chain off (`domain`, `ip`, `hash`, or `cve`).
- **`expectedExecutionMode`** — the value the assertions expect to see in the response (`demo` or `live`).

The first two let you point the same collection at different servers and different fixtures; the third is what makes mode-precedence assertable.

Select **Ross Moda IoC Triage — Demo** in the environment dropdown. Confirm:

- `baseUrl` reads `http://127.0.0.1:7777`
- `expectedExecutionMode` reads `demo`

You are configured.

---

## 3. Run the tests in the Postman app

The Postman app — desktop or web — has two ways to execute a collection:

- **The Collection Runner**, opened from the more-actions menu (`...`) next to the collection name, runs everything sequentially with a single click and shows you a summary.
- **Individual requests**, sent one at a time by clicking them in the sidebar and pressing **Send**, which is useful when you are debugging a single assertion.

Both modes share the same execution model, so the question of which to use is purely ergonomic.

Open the Collection Runner. Confirm the environment dropdown reads **Ross Moda IoC Triage — Demo**. Click **Run Ross Moda IoC Triage API**.

The runner executes folders top to bottom. In about a second on a modern machine, you should see thirty-seven green checks and a duration in the neighborhood of `1,200ms`.

What just happened is worth slowing down for. Before the first request fires, a *collection-level pre-request script* (visible in the **...** menu under **Edit** → **Pre-request Scripts**) makes one HTTP call to `${baseUrl}/openapi.json` and stores the response's `components.schemas` block in a collection variable. This happens once per run, not once per request. Every contract assertion downstream reads from that cached variable. If the server is offline, this fetch silently fails and the schema assertions skip — which is one reason `/health` is the first request: if liveness fails, you know to stop before debugging anything else.

Inside the `02 — Triage (demo mode)` folder, the request named `POST /api/v1/triage (domain via example chain)` shows the chaining pattern that holds the suite together:

1. The **Pre-request Script** tab calls `GET /api/v1/examples/{{iocType}}` and stores the response's `payload` field as a string in the variable `examplePayload`.
2. The request body is then literally `{{examplePayload}}` — Postman substitutes the variable at send time.
3. The effect is that the same JSON file (`fixtures/examples/domain.json`) is both the API's published example payload *and* the test's input.

Update one, both update. There is no second copy to forget about.

The **Tests** tab is where the assertions live. Each `pm.test("description", () => { ... })` block is one assertion in the count. The block named `matches TriageApiResponse schema` does the heaviest work:

- It pulls the cached schemas out of the collection variable.
- It compiles `TriageApiResponse` with AJV.
- It validates the response body.

If a Pydantic model in `web/schemas.py` grows a required field, this assertion fails on the next run — not because someone edited the test, but because the server's own schema reported a new required field and the response didn't carry it.

The folder also contains a negative-path request named `CVE — fixture miss`. Sending it returns `503 DEMO_FIXTURE_MISSING`. This is deliberate:

- There is no fixture file for CVE inputs in `fixtures/demo/`.
- The test asserts the failure mode: in demo mode, an unresolvable IOC must hard-fail with a structured error envelope, not silently degrade to a live API call.
- It is the single assertion that proves mode precedence at runtime.

When the run finishes, the **Run Summary** view shows per-request pass/fail counts, response times, and the response body of any request you click. If everything is green, you have validated that your container, the collection, and the schema are in agreement. You are ready to wire this into CI.

---

## 4. Run the tests in GitHub Actions

The workflow at `.github/workflows/postman.yml` runs the same collection on every push and every pull request. It already exists; what follows is a tour of what it does and why each step is shaped the way it is.

A GitHub Actions *job* is a sequence of steps executed on a freshly provisioned virtual machine — in this case `ubuntu-latest`. The job in this repository is named `postman-demo`, and it executes these steps in order:

1. **Setup.** The first three steps check out the code, install Python 3.11 (for the server), and install Node.js 20 (for Newman). These are stock `actions/checkout@v4`, `actions/setup-python@v5`, and `actions/setup-node@v4` from GitHub's marketplace. They take a few seconds each.

2. **Install dependencies.** Two install steps follow:
   - `pip install -r requirements.lock` gives the runner the exact dependency tree the container would have — same versions, same transitive resolutions.
   - `npm install -g` installs Newman and two reporters (`newman-reporter-junitfull` and `newman-reporter-htmlextra`) that produce the artifacts CI uploads at the end of the run.

3. **Boot the server.** This is where CI departs from the local workflow you just ran. Rather than starting the container, CI starts `uvicorn` directly with `python -m uvicorn web.app:app --host 127.0.0.1 --port 7777`. The reasons are speed and isolation:
   - Skipping the Docker build cuts roughly thirty seconds off the run.
   - The GitHub runner is already a disposable VM, so the container's isolation guarantees buy nothing.

   The environment variable `IOC_TRIAGE_DEMO_MODE=true` is set at the job level, so the server boots in demo mode and the agent never tries to resolve API keys.

4. **Wait for readiness.** The next step is a polling loop:
   - Thirty attempts maximum.
   - One-second sleep between each.
   - Calls `/health` until it returns 200 or the loop expires.

   This step exists because `uvicorn` returns control to the shell before the FastAPI lifespan hook finishes — the process is alive a beat before the application is ready. Without this gate, the next step would race the server.

5. **Latency gate.** A second curl call measures `/health`'s response time and compares it to `HEALTH_LATENCY_THRESHOLD_MS` (default 1000 ms). This is a coarse performance regression check. Liveness probes are supposed to be cheap; a slow `/health` usually means something is wrong with startup, not the network.

6. **Run Newman.** The Postman collection runs via `./scripts/postman.sh full`. Newman uses the same JavaScript sandbox as the Postman runner, so the assertions are byte-for-byte the ones you just watched go green in the app. Four reporters are emitted in parallel:
   - **CLI summary** captured to `newman-cli-summary.txt`
   - **JSON report** at `artifacts/postman/newman-report.json`
   - **JUnit XML** at `newman-junit.xml`
   - **HTML report** at `newman-report.html`

7. **The assertion-count gate.** This is the step that protects the test suite from being neutered. It reads the JSON report with `jq` and enforces two conditions:

   ```bash
   total=$(jq '.run.stats.assertions.total' artifacts/postman/newman-report.json)
   failed=$(jq '.run.stats.assertions.failed' artifacts/postman/newman-report.json)
   test "$total" -ge 25 || exit 1
   test "$failed" -eq 0
   ```

   - The first check (`total >= 25`) prevents a future contributor from "fixing" a flaky assertion by deleting it.
   - The second is the obvious one: no failures allowed.

   Either failing exits the job non-zero, which fails the workflow, which (if you configure branch protection) blocks the pull request from merging.

8. **Upload artifacts.** The final step runs `actions/upload-artifact@v4` with `if: always()`. That `if: always()` is load-bearing. Without it, a failing build would throw away the very reports you need to debug the failure. With it, the following are uploaded regardless of pass or fail:
   - JUnit XML
   - JSON report
   - HTML report
   - CLI summary
   - The server's stdout (`server.log`)

   You download them from the **Actions** tab on GitHub.

To see all of this happen:

1. Push any branch.
2. Open the repository on GitHub.
3. Click **Actions**.
4. Click the most recent run.
5. Click the `postman-demo` job.

Each step expands to show its output. A green checkmark next to the job name and a duration around forty-five seconds is the steady-state expectation.

To make CI failure block merges — the actual point of having CI:

1. Open **Settings** → **Branches** → **Add branch ruleset**.
2. Target the `main` branch.
3. Enable **Require status checks to pass before merging**.
4. Add `postman-demo` to the required checks.

Until you do this, CI is informational; after, it is enforcing.

---

## 5. Run the tests with Newman and the GitHub CLI

There are two reasons to drive the suite from a terminal rather than the Postman app:

- **A tight inner loop.** When you are editing a test or a server-side schema, the round-trip from "edit file" to "see result" is shorter at the command line than in the GUI.
- **Parity with CI.** By running the exact same `./scripts/postman.sh` command CI runs, you can reproduce a CI failure locally without pushing a commit to chase it.

Install Newman once:

```bash
npm install -g newman newman-reporter-junitfull newman-reporter-htmlextra
```

Newman is Postman's headless test runner. It loads the same collection JSON, executes the same JavaScript sandbox, and writes the same kinds of reports. There is no separate test framework underneath — `pm.test` and `pm.expect` behave identically in both runtimes. If you are coming from JavaScript testing, Newman's assertion library is Chai, exposed through `pm.expect`.

The repository wraps Newman in `scripts/postman.sh`, which provides two modes:

```bash
./scripts/postman.sh smoke    # liveness + examples only, ~1 second
./scripts/postman.sh full     # every folder, all reporters, ~2 seconds
```

- **`smoke` mode** passes `--bail` to Newman, which exits on the first failed assertion. It is meant for a pre-commit hook — fast, opinionated, advisory.
- **`full` mode** is what CI runs: it produces every reporter format and writes the artifact tree to `artifacts/postman/`. After it finishes, it parses its own JSON report with `jq` and prints a one-line summary, just like the CI gate does.

If you want to inspect the HTML report locally, open `artifacts/postman/newman-report.html` in any browser.

The GitHub CLI (`gh`) complements Newman by letting you drive the *remote* runs without leaving the terminal. After authenticating once with `gh auth login`, you have a handful of commands worth knowing:

```bash
gh workflow list                              # show configured workflows
gh workflow run postman.yml                   # trigger postman.yml on the current branch
gh run list --workflow=postman.yml --limit=5  # show recent runs and their status
gh run watch                                  # tail the latest in-progress run
gh run view --log-failed                      # print only the failed steps' logs
gh run download <run-id>                      # pull the uploaded artifacts locally
```

The pattern that pays off in practice, when CI fails:

1. Run `gh run view --log-failed` to read the failing step.
2. Run `gh run download` to pull `newman-report.html` to your machine.
3. Open it in a browser. The HTML report shows the failed request's body, headers, response, and the specific assertion that failed — usually enough to fix the issue in one pass without ever leaving the terminal.

You now have three independent ways to run the same tests:

- **Postman's app**
- **Newman on your machine**
- **GitHub Actions in the cloud**

All three execute the same collection, against the same kind of server, and report the same assertions. There is no path by which one passes and another fails for reasons of "the test environment was different." That is the point.

---

## When something breaks

| What you see | Why it's happening | What to do |
|---|---|---|
| `ECONNREFUSED` on every Postman request | The container isn't running, or the port mapping is wrong. | `docker compose ps` to confirm; restart with the Step 1 command. |
| All triage requests return `503 DEMO_FIXTURE_MISSING` | The container started without `IOC_TRIAGE_DEMO_MODE=true`. | Restart with the variable set. |
| `expectedExecutionMode` assertion fails | The wrong environment is selected in Postman. | Choose **Ross Moda IoC Triage — Demo** in the environment dropdown. |
| Schema assertion fails after a server-side change | A Pydantic model changed; the OpenAPI schema reflects the new shape; the collection just enforced the change. | Decide if the change is intentional. If yes, update the consumers and proceed. If no, revert the model. |
| Local Newman passes, CI fails | Almost always a timing issue: the server wasn't ready when Newman started. | Read `server.log` in the CI artifacts; if the latency gate failed, the server was slow to boot. |
| Postman runs the collection but no schema assertions execute | The collection-level pre-request fetch of `/openapi.json` failed silently — usually because `baseUrl` is wrong. | Verify `/openapi.json` returns 200 from your browser using the environment's `baseUrl`. |

---

## Where to go next

- **[`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md)** — the click-by-click runbook to keep open during a live demo.
- **[`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md)** — the presenter narration that pairs with the text-only slide notes.
- **[`../docs/API.md`](../docs/API.md)** — the structured API reference: endpoints, schemas, error codes.
