# Postman Demo — Technical Presenter Script

> **FlowRun IoC Triage API — 4 Minute Walkthrough**
>
> Slide-by-slide narration with technical depth on the CI/CD pipeline,
> automation layer, test success/failure paths, the data products, and
> human-in-the-loop decision points.
>
> Use this for rehearsal. The lean click-and-type runbook lives in
> [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md). Slide
> notes inside `FlowRun_Postman_Demo.pptx` carry tight prompts for
> Presenter View.

---

## What this document emphasizes

Each slide covers, where relevant:

- **Pipeline flow** — what triggers what, and what the data path looks like
- **API & automation layer** — what's actually executing under the request
- **Test outcomes** — what success means, what failure means, what gets emitted
- **Actionable data** — where the results go and who consumes them
- **Human decision points** — when a person has to step in

Total time budget: **4:00**.

---

## Table of contents

- [Pre-flight](#pre-flight)
- [Slide 1 — Title (0:00 → 0:15)](#slide-1--title-000--015)
- [Slide 2 — Four pillars (0:15 → 1:00)](#slide-2--four-pillars-015--100)
- [Slide 3 — Orientation (1:00 → 1:30)](#slide-3--orientation-100--130)
- [Slide 4 — Timeline (1:30 → 2:30)](#slide-4--timeline-130--230)
- [Demo block — live Postman (2:30 → 3:20)](#demo-block--live-postman-230--320)
- [Slide 5 — Problems prevented (3:20 → 3:45)](#slide-5--problems-prevented-320--345)
- [Slide 6 — Close (3:45 → 4:00)](#slide-6--close-345--400)
- [Technical FAQ](#technical-faq)

---

## Pre-flight

Works identically with Docker or Podman — substitute `podman` for
`docker` in the commands below.

```bash
# 1. Build the image (first run only) and start the API in demo mode (terminal 1)
docker build -t flowrun-streamlet-ioc-triage:0.0.33 .
docker run -d --name flowrun-demo -p 127.0.0.1:7777:7777 \
  -e FLOWRUN_DEMO_MODE=true -e FLOWRUN_NO_PROMPT=1 \
  flowrun-streamlet-ioc-triage:0.0.33

# 2. Verify (terminal 2)
curl -s http://127.0.0.1:7777/health
# Expect: {"status":"ok","trace_endpoint":...}

# 3. Teardown — after the demo
docker rm -f flowrun-demo
```

Demo mode serves every response from local fixtures baked into the image —
no `.env` file and no API keys are needed.

Postman: import `postman_collection.json`, set environment to
`FlowRun IoC Triage — Demo`, expand the collection tree.

---

## Slide 1 — Title (`0:00 → 0:15`)

### What's on the slide

Dark navy. Title *FlowRun IoC Triage API*. Subtitle *Contract testing with
Postman*. Stat strip: `v0.0.33  |  37 assertions  |  5 folders  |  ~1s wall time`.

### Narration

> "Over the next four minutes I'll walk you through how we use Postman and
> Newman to validate a FastAPI security service in CI — what runs, what it
> tests, where the results go, and where a human still has to make a call."

### Technical anchor

The stat strip up top is real, not decorative: the collection has **five
folders**, **thirty-seven assertions**, and end-to-end wall time of roughly
**one second** when run via `newman run` against a local API.

**Transition** → *"First — what we actually test."*

---

## Slide 2 — Four pillars (`0:15 → 1:00`)

### What's on the slide

Four cards: **Liveness · Contract · Behavior · Negative paths.** Each
card carries a monospace detail pill (`GET /health < 200ms`, etc.).

### Narration with technical depth

> "Every assertion in the collection maps to one of four pillars."

**Pillar 1 — Liveness.** A single `GET /health` request. Asserts HTTP 200,
body shape `{status: "ok", trace_endpoint: ...}`, and response time below
200ms. This is the only endpoint that does no agent work — it never touches
the LangGraph or the threat-intel integrations. If liveness fails, nothing
else matters; the suite halts.

**Pillar 2 — Contract.** The big one. Every triage response is validated
against the live OpenAPI document at `/openapi.json`. FastAPI auto-generates
that document from the Pydantic models in `web/schemas.py` — when a
developer changes a model, the schema changes, and Postman's AJV validator
picks up the new shape on the next run. **No hand-maintained schema copy
to drift.**

**Pillar 3 — Behavior.** Three execution modes — `live`, `demo`, and
`mock` — must stay separated. The collection asserts that a request to
`POST /api/v1/triage` with `FLOWRUN_DEMO_MODE=true` returns
`execution_mode: "demo"` and a non-empty `fixture_id`. **Demo mode is never
allowed to silently fall through to live.** That's not just convention;
the assertion enforces it.

**Pillar 4 — Negative paths.** Empty IOC → `400 IOC_EMPTY`. Unknown
example type → `404 EXAMPLE_NOT_FOUND`. CVE with no demo fixture →
`503 DEMO_FIXTURE_MISSING`. Each error has a structured envelope with a
machine-readable `code`, a human-readable `message`, and an optional
`details` object — the same envelope across every error path.

### Actionable output

A failing assertion in any pillar produces three artifacts: JUnit XML
(rendered in GitHub's test view), a JSON report with the request, response,
and assertion message, and an HTML report for human inspection. **You can
reproduce the failure without rerunning.**

**Transition** → *"Three quick definitions before we look at this in action."*

---

## Slide 3 — Orientation (`1:00 → 1:30`)

### What's on the slide

Glossary: Postman / Collection / Newman. Right side: a fake terminal showing
green checkmarks and `37 assertions   0 failed   1.24 s`.

### Narration with technical depth

> "Three terms to ground the rest of this."

**Postman** — desktop app, sends HTTP, runs JavaScript assertions in the
sandbox after each response. Assertions use `pm.expect` (Chai under the
hood) plus optional libraries like AJV for schema validation.

**Collection** — a serialized JSON file (`postman_collection.json`)
containing requests, folder structure, pre-request scripts, test scripts,
and variables. Same file Postman GUI uses, same file Newman uses. Live in
git, reviewed in PRs like any other code artifact.

**Newman** — Node.js CLI that runs collections headless. Same JavaScript
sandbox, same assertion semantics, different runtime. **This is what makes
the demo/CI equivalence possible** — your laptop and the GitHub runner are
executing identical code paths.

### What the green checks actually mean

Each green check is one `pm.test(...)` block. The wall-clock number next to
it is response time, not assertion time. A green run with `37 assertions, 0
failed` means Newman exits 0; in CI that exit code is what the build gate
consumes.

**Transition** → *"Before we open Postman, let me show you when this fires."*

---

## Slide 4 — Timeline (`1:30 → 2:30`)

### What's on the slide

Horizontal arrow: Write code → Commit → Push to GitHub → Merge & ship.
Three checkpoint cards hang from the timeline.

### Narration with technical depth

> "Same Postman collection, three checkpoints along the developer workflow,
> each catching a different class of problem."

**Checkpoint 1 — `./scripts/postman.sh smoke` (pre-commit).**
- Runs only the `00 — Liveness` and `01 — Examples` folders.
- `--bail` flag means Newman exits on the first failure.
- Wall time ~1 second.
- **Trigger:** developer runs the script manually or via a pre-commit hook.
- **Success path:** zero output to deal with; commit proceeds.
- **Failure path:** Newman prints the failed assertion, developer sees it
  in their terminal, commit is *not* blocked automatically — pre-commit is
  advisory, not enforced. Bypassable with `git commit --no-verify`.

**Checkpoint 2 — `./scripts/postman.sh full` (pre-push).**
- Runs every folder.
- Four reporters in parallel: `cli`, `json`, `junitfull`, `htmlextra`.
- Artifacts written to `artifacts/postman/`:
  - `newman-report.json` — machine-readable, gates the build
  - `newman-junit.xml` — for GitHub's test viewer
  - `newman-report.html` — for human post-mortem
  - `newman-cli-summary.txt` — terminal output captured
- Wall time ~2 seconds.

**Checkpoint 3 — `.github/workflows/postman.yml` (CI on push).**
This is where the gating actually happens. Walk through the steps:
1. GitHub Actions runner spins up on `ubuntu-latest`.
2. Installs Python 3.11, Node 20, Newman + reporters.
3. Boots uvicorn with `FLOWRUN_DEMO_MODE=true` — **no API keys needed**,
   no outbound network to threat-intel providers.
4. Polls `/health` for 30 seconds until it returns 200.
5. Checks `/health` latency against `HEALTH_LATENCY_THRESHOLD_MS`
   (default 1000ms).
6. Runs `./scripts/postman.sh full`.
7. Parses `newman-report.json` with `jq`:
   ```bash
   total=$(jq '.run.stats.assertions.total'  newman-report.json)
   failed=$(jq '.run.stats.assertions.failed' newman-report.json)
   test "$total" -ge 25 || exit 1
   test "$failed" -eq 0
   ```
8. Uploads artifacts **always** (`if: always()`) — even on failure, so the
   debugging data is always available.

### When the human gets involved

- **CI failure** → GitHub's PR check turns red. Required-status branch
  protection rule blocks merge. The reviewer opens the JUnit XML in
  GitHub's test view, sees which assertion failed, opens the HTML report
  for the request/response.
- **Pre-commit failure** → developer sees it locally, decides whether to
  fix or `--no-verify` past it. CI catches them later if they bypass.
- **Latency-only failure** → ambiguous, may indicate flaky runner; human
  judgment call whether to rerun.

**Transition** → *"Let me alt-tab to Postman and show you what actually runs."*

---

## Demo block — live Postman (`2:30 → 3:20`)

Slide 4 stays projected while you alt-tab to Postman.

### Beat 1 — The collection structure (`2:30`)

Click the collection in left nav. Five folders visible.

> "Five folders, organized by intent. `00 — Liveness` is one request.
> `01 — Examples` validates the fixture-fetch endpoint. `02 — Triage (demo
> mode)` is the meat — schema validation, mode assertions. `03 — Triage
> (mock mode)` is the canned-response variant. `04 — Negative & contract`
> hits the error envelopes."

### Beat 2 — Pre-request script chain (`2:40`)

Click `02 — Triage (demo mode)` → `POST /api/v1/triage (domain via example
chain)` → **Pre-request Script** tab.

> "Before this request fires, Postman runs this script. It calls
> `GET /api/v1/examples/domain` to fetch the canonical payload from
> `fixtures/examples/domain.json`, deserializes it, and stores it as a
> Postman variable. The actual request body is `{{examplePayload}}` —
> resolved at send time.
>
> **Single source of truth:** the same JSON file is the API's example
> endpoint *and* the test payload. Update one, both update."

### Beat 3 — The schema assertion (`2:55`)

**Tests** tab → scroll to the `matches TriageApiResponse schema` block.

> "Here's the contract test. The collection-level pre-request script
> already fetched `/openapi.json` once and cached `components.schemas` in a
> collection variable. This test pulls `TriageApiResponse`, compiles it
> with AJV, and validates the response body. If the Pydantic model in
> `web/schemas.py` adds a field, the OpenAPI doc reflects it on the next
> server start, and this test picks it up automatically."

### Beat 4 — Send the request (`3:05`)

Click **Send**. Test Results pane shows green.

> "Eight green. Look at what's asserted: status 200, `execution_mode` is
> `demo`, `fixture_id` is non-empty, schema validates, severity is a known
> band, score is between 0 and 1, timings are present, case_id round-trips."

### Beat 5 — Negative path: fixture-miss (`3:10`)

Click `CVE — fixture miss` → **Send**.

> "Same demo mode. Posting a real CVE. There's no `cve__*.json` or
> `default__cve.json` fixture in `fixtures/demo/` — this is deliberate.
>
> The server resolves the IOC type (CVE), looks for two fixture keys, finds
> neither, and raises `503 DEMO_FIXTURE_MISSING`. The error envelope has a
> code, a message, and a `details` object listing which fixture keys were
> checked.
>
> **This is the mode-precedence assertion.** Demo mode is not allowed to
> degrade to live. A real-world CVE will not silently trigger an outbound
> call to NIST NVD. The 503 is the contract."

### Beat 6 — Runner (`3:18, optional`)

Click **Runner** → select collection → **Run**.

> "Same collection, Postman's UI runner. Five folders, 37 assertions,
> green, about a second. Identical to what `newman run` does in CI."

Alt-tab back to deck → advance to slide 5.

---

## Slide 5 — Problems prevented (`3:20 → 3:45`)

### Narration with technical depth

> "Every row is a failure mode test suites hit eventually. Two worth
> calling out from a systems perspective."

**Row 1 — Tests drift from the code.**
> "Hand-written schemas drift because they require *discipline* to keep in
> sync. Our schemas come from `/openapi.json` at runtime — FastAPI emits it
> from Pydantic v2 models, no human in the loop. The schema check is
> impossible to leave stale without also breaking the server."

**Row 4 — Performance regressions reach production.**
> "Every Postman request has a `pm.expect(pm.response.responseTime).to.be.
> below(N)` assertion. Per-folder budgets: liveness 200ms, examples 300ms,
> triage 500ms. A response that's correct but slow fails the build. The CI
> gate doesn't distinguish between functional regressions and performance
> regressions — both block the merge."

### When the human gets involved (still)

> "These patterns reduce — they don't eliminate — the human role. A failed
> contract assertion still requires a human to decide: is this a schema
> change we *intended*, or a regression? A blown latency budget still
> requires a human to decide: rerun, investigate, or accept the new
> baseline. **The automation surfaces the question; humans answer it.**"

**Transition** → *"One thing to take away."*

---

## Slide 6 — Close (`3:45 → 4:00`)

### Narration

> "Same Postman collection. Three checkpoints. Zero drift.
>
> If you want to verify what I showed you — three commands on the left,
> sixty seconds end to end, no API keys because demo mode runs from local
> fixtures.
>
> The repo links on the right cover the runbook, the API reference, the
> raw collection JSON, and the CI workflow YAML. Everything you saw is
> reproducible.
>
> Questions to Jeremiah Ross, `jr@ross.moda`."

---

## Technical FAQ

### Q: How does demo mode prevent live API calls?

**Source of truth:** `web/app.py::triage_api` is the only function that
resolves execution mode. When `FLOWRUN_DEMO_MODE=true`, the function
short-circuits to `web/demo_mode.py::load_demo_result` and never reaches
the LangGraph dispatcher (`agent/graph.py::build_graph`). A missing fixture
raises `FileNotFoundError`, which the handler converts to a structured
`503 DEMO_FIXTURE_MISSING`. There is no code path from demo mode to a live
integration call. The CVE fixture-miss test enforces this.

### Q: What happens when the OpenAPI document changes?

Pydantic v2 model change → server restart → new `/openapi.json` → next
collection run picks it up via the pre-request fetch → AJV recompiles
`TriageApiResponse` → existing assertions either continue passing
(non-breaking change) or fail (breaking change). The failure is the
signal; the human decides whether the breakage was intentional.

### Q: How is CI configured to actually block merges?

The Postman job is referenced in GitHub branch protection rules as a
required status check. If the job exits non-zero, the PR cannot be merged
without an admin override. The job exits non-zero when (a) the health
latency check fails, (b) `jq` finds fewer than 25 total assertions, or
(c) `jq` finds any failed assertions. Two of these three conditions are
sanity checks on the collection itself — preventing someone from
neutralizing tests by deleting them.

### Q: Where do the test results actually go?

Four destinations, all under `artifacts/postman/`:
1. **`newman-report.json`** — machine-readable; consumed by `jq` for the
   gating logic and by any downstream dashboard or alert pipeline.
2. **`newman-junit.xml`** — consumed by GitHub Actions' test viewer; gives
   you per-assertion pass/fail rendered inline in the PR.
3. **`newman-report.html`** — opened by humans during incident review;
   includes request/response bodies for every failed assertion.
4. **`newman-cli-summary.txt`** — the boxed terminal output, captured for
   logs.

GitHub Actions uploads all four with `if: always()`, so debugging data
exists whether the run passed or failed.

### Q: What about live-mode testing?

The same collection runs against live mode by switching the environment
file. `postman_environment.local.json` sets `expectedExecutionMode=live`.
Schema assertions still pass (response shape doesn't change between
modes). Mode-precedence assertions verify `execution_mode: "live"` and
`fixture_id: null`. Live runs are *not* part of the CI gate — they're for
manual smoke testing against a real backend, when API keys are configured.

### Q: When does a human have to step in?

| Trigger | Human action |
|---------|--------------|
| CI gate fails on a PR | Review JUnit / HTML report, decide: fix code, fix tests, or revert |
| Pre-commit fails locally | Fix immediately, or `--no-verify` and explain in PR |
| Schema assertion fails | Decide if model change was intentional; update consumers |
| Latency budget fails | Investigate; either fix performance or rebaseline budget |
| Mode-precedence assertion fails | **High-priority** — demo mode is leaking, investigate |
| Negative-path assertion fails | Error envelope changed; coordinate with API consumers |
| Live triage returns CRITICAL severity (production) | LangGraph escalation gate fires; analyst confirms before action |

The last row is the only place a human is structurally required *during
runtime*, not just at review time. Everything above the line is humans
reviewing automation output asynchronously.

---

## Cross-references

- [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md) — lean
  click-and-type runbook
- [`POSTMAN_DEMO.md`](POSTMAN_DEMO.md) — runbook with worked scenarios
- [`API.md`](API.md) — endpoint reference and error codes
- `FlowRun_Postman_Demo.pptx` — the deck (slide notes for Presenter View)
- `postman_collection.json` — the collection
- `.github/workflows/postman.yml` — the CI pipeline
