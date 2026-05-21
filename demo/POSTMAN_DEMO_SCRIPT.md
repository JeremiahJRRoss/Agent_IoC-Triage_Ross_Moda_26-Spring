# Postman Demo — Presenter Script

There is a difference between knowing a thing works and showing a thing works. The first is a property of the system; the second is a property of the demo. This script is the rehearsal companion for the second. It carries narration, timing, and the technical claims you make at each beat. Read it once before you present, and once more the morning of.

The companion runbook is [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md). The runbook is for your hands. This file is for your voice.

Total budget: four minutes. Slides bracket the demo on both sides — about ninety seconds of context before the live walkthrough, ninety seconds after, and roughly sixty seconds in Postman itself. Six beats inside Postman. Six minutes of practice will get you to four minutes of delivery.

---

## What this demo is really about

The audience is going to watch you send HTTP requests and see green checkmarks. That is the visible layer. The argument underneath — the thing you are actually arguing for — is harder to see. The argument is that *the same artifact runs identically in three places* (Postman's app, Newman on a developer's machine, GitHub Actions in the cloud), and that *the contract under test is derived from the running server rather than maintained by hand*. Both of those properties are invisible if you only look at the green checks. Your narration is what makes them visible.

The corollary is what to leave out. Resist the urge to explain LangGraph, OpenTelemetry, or the threat-intel weighting formulas. Those are the agent's product story. This is the testing infrastructure story. They share a repository; they are different talks.

---

## Demo mode versus live mode — the one paragraph

Somewhere in slide 2 or slide 4, depending on questions, you need to explain why what the audience is about to see is not a stunt. The explanation goes like this:

> "What I'm about to show you runs in demo mode. The server reads its responses from JSON files baked into the container — no API keys, no outbound calls to VirusTotal or any other vendor, deterministic to the millisecond. The same Postman collection runs against the live server too, with real API integrations, and the same thirty-seven assertions pass. What changes between the two is one field in the response: `execution_mode` is either `demo` or `live`, and the test enforces that the value matches what the environment expects. So demo mode isn't a softer test — it's the same test, with a different proof of where the data came from. The reason to demo in demo mode rather than live mode is that vendor rate limits and weather have no business being part of a four-minute presentation."

If they ask why the assertions still pass when the data source changes: because the *shape* of the response is identical regardless of source, and the schema asserts the shape. The data shape is part of the API; the data values are not.

---

## Pre-flight commands

Forty-five minutes before the demo, with Docker running:

```bash
# Build and start the demo-mode server. Substitute podman for docker if you prefer.
FLOWRUN_DEMO_MODE=true docker compose up --build -d

# Confirm liveness. Expect: {"status":"ok","trace_endpoint":"..."}.
curl -s http://127.0.0.1:7777/health
```

Open Postman. Confirm the environment dropdown reads **FlowRun IoC Triage — Demo**. Run the Collection Runner once. Confirm thirty-seven green checks. If any are red, debug now — not during.

Open `FlowRun_Postman_Demo.pptx` to slide 1. Switch to Presenter View if you have a second display.

Teardown after the demo:

```bash
docker compose down
```

---

## Slide 1 — Title (0:00 → 0:15)

### What's on screen

Dark navy. Title: *FlowRun IoC Triage API*. Subtitle: *Contract testing with Postman*. Stat strip across the bottom: `v0.0.33  |  37 assertions  |  5 folders  |  ~1s wall time`.

### Narration

> "Over the next four minutes I'll walk you through how we use Postman and Newman to validate a FastAPI security service in CI. What runs, what it tests, where the results go, and where a human still has to make a call about whether to trust a green build."

### The claim underneath

The stat strip is real, not decorative. Five folders, thirty-seven assertions, end-to-end execution under a second. These numbers matter because the suite is small enough to run in pre-commit hooks, large enough to actually catch contract regressions. If it took a minute, no one would run it before pushing. If it had ten assertions, it would catch nothing.

**Transition.** *"First — what we actually test."*

---

## Slide 2 — The four pillars (0:15 → 1:00)

### What's on screen

Four cards across the slide: *Liveness*, *Contract*, *Behavior*, *Negative paths*. Each carries a monospace detail pill underneath — `GET /health < 200ms`, `OpenAPI from running server`, `execution_mode enforced`, `503 envelopes`.

### Narration with technical depth

> "Every assertion in the suite maps to one of four pillars."

**Pillar 1 — Liveness.** One request. `GET /health`. Asserts status 200, body shape `{status: "ok", trace_endpoint: …}`, and response time below 200 milliseconds. The endpoint does no agent work, makes no outbound calls; it exists so an orchestrator can ask the cheapest possible question. If liveness fails, nothing else matters and the suite halts.

**Pillar 2 — Contract.** The largest pillar. Every triage response is validated against the OpenAPI document served at `/openapi.json`. FastAPI generates that document from the Pydantic models in `web/schemas.py` — no human edits it. When a developer changes a model, the schema changes on the next server restart, and the Postman collection picks it up on the next run. There is no separate schema file to keep in sync. The contract under test is the contract the server actually publishes.

**Pillar 3 — Behavior.** Three execution modes — `live`, `demo`, and `mock` — must stay separated at runtime. The collection asserts that a demo-mode request returns `execution_mode: "demo"` and a non-empty `fixture_id`. Demo mode is never permitted to silently fall through to live. That's enforced by exactly one assertion in the negative-path folder, and we'll come back to it.

**Pillar 4 — Negative paths.** Empty IOC returns `400 IOC_EMPTY`. Unknown example type returns `404 EXAMPLE_NOT_FOUND`. A CVE submitted in demo mode, with no fixture present, returns `503 DEMO_FIXTURE_MISSING`. Every error carries a structured envelope: `error.code`, `error.message`, optional `error.details`. The same envelope shape across every error path. Consumers can write a single handler.

### The claim underneath

A failing assertion in any pillar produces four artifacts: a CLI summary, a JSON report, a JUnit XML rendered in GitHub's test view, and an HTML report opened in a browser. You can reproduce the failure without rerunning the suite.

**Transition.** *"Three quick definitions before we look at this in motion."*

---

## Slide 3 — Orientation (1:00 → 1:30)

### What's on screen

Three boxed terms. *Postman*. *Collection*. *Newman*. To the right, a faux terminal showing `37 assertions, 0 failed, 1.24 s` in green.

### Narration with technical depth

> "Three terms to ground the rest of this."

**Postman** is the desktop and web client. It sends HTTP requests and runs JavaScript assertions in a sandbox after each response returns. The assertion library is Chai, exposed through `pm.expect`. The schema validator is AJV.

**A collection** is a serialized JSON file — `postman_collection.json` in this repository. It carries requests, folder structure, pre-request scripts, test scripts, and variables. The same file Postman's GUI imports, the same file Newman runs from the command line. It lives in git and gets reviewed in pull requests like any other code artifact.

**Newman** is Postman's headless command-line runner. Node.js. Same JavaScript sandbox, same assertion semantics, different runtime. This is what makes the local-CI equivalence possible — your laptop and the GitHub Actions runner execute identical code paths against identical inputs. If something passes here and fails there, the cause is environmental, not test-logical.

### What the green checks actually mean

Each green check is one `pm.test(...)` block. The wall-clock number next to it is response time, not assertion time. A green run with `37 assertions, 0 failed` means Newman exits zero. In CI, that exit code is what the build gate consumes.

**Transition.** *"Before we look in Postman, let me show you when this fires."*

---

## Slide 4 — Timeline (1:30 → 2:30)

### What's on screen

Horizontal arrow: *Write code → Commit → Push → Merge & ship*. Three checkpoint cards hang from the arrow.

### Narration with technical depth

> "Same Postman collection. Three checkpoints along the developer workflow. Each catching a different class of problem."

**Checkpoint 1 — pre-commit.** The developer runs `./scripts/postman.sh smoke`. Newman runs only the `00 — Liveness` and `01 — Examples` folders with `--bail`, which exits on the first failure. Wall time is about a second. This catches the obvious: server unreachable, example fixture broken, contract clearly violated. It's advisory — pre-commit isn't enforced by the repository — and a developer can `--no-verify` past it. The point isn't to block; the point is to surface fast.

**Checkpoint 2 — pre-push.** The developer runs `./scripts/postman.sh full`. Every folder. Four reporters in parallel — CLI, JSON, JUnit XML, HTML — writing to `artifacts/postman/`. Wall time about two seconds. This is the full local rehearsal of what CI will run, and it produces the same artifacts.

**Checkpoint 3 — CI on push.** This is where gating actually happens. The workflow at `.github/workflows/postman.yml` runs on every push and every pull request. It checks out the code, installs Python and Node, installs Newman, boots the server in demo mode, polls `/health` until ready, runs `./scripts/postman.sh full`, then parses the JSON report with `jq`:

```bash
total=$(jq '.run.stats.assertions.total'  newman-report.json)
failed=$(jq '.run.stats.assertions.failed' newman-report.json)
test "$total" -ge 25 || exit 1
test "$failed" -eq 0
```

Two gates, both load-bearing. The first prevents a future contributor from "fixing" a flaky test by deleting it — the suite must have at least twenty-five assertions, or the build fails. The second is the obvious one: no failures allowed. Either failing exits the job non-zero, and a branch-protection rule blocks the pull request from merging.

Artifacts upload with `if: always()`. That clause is essential — without it, a failing build would discard the very reports you need to debug the failure.

### When the human gets involved

> "These patterns reduce the human role. They don't eliminate it."

A failed contract assertion still needs someone to decide: is this a schema change we intended, or a regression? A blown latency budget still needs someone to decide: rerun, investigate, or accept the new baseline. The automation surfaces the question; humans answer it.

**Transition.** *"Let me alt-tab to Postman and show you what actually runs."*

---

## The demo block — live in Postman (2:30 → 3:20)

Slide 4 stays projected. Alt-tab to Postman. Six beats in roughly fifty seconds.

### Beat 1 — The collection (2:30)

*Click the collection name. Folder tree expands.*

> "Five folders, organized by intent. `00 — Liveness` is one request. `01 — Examples` validates the fixture-fetch endpoint that other tests chain off. `02 — Triage (demo mode)` is the meat — schema validation, mode assertions, the happy path. `03 — Triage (mock mode)` is the canned-response variant for schema-only contract checks. `04 — Negative & contract` hits the error envelopes."

Point at the environment dropdown.

> "We're in the Demo environment. There's a Local environment that points at a live server — same collection, different value for `expectedExecutionMode`. The assertions don't change."

### Beat 2 — The pre-request chain (2:40)

*Click `02 — Triage (demo mode)` → `POST /api/v1/triage (domain via example chain)` → **Pre-request Script** tab.*

> "Before this request fires, Postman runs the script you see here. It calls `GET /api/v1/examples/domain` to fetch the canonical payload — sourced from `fixtures/examples/domain.json` in the repo — and stores it in a variable. The actual request body is `{{examplePayload}}`, resolved at send time. The same JSON file is the API's documented example and the test's input. Update one, both update. There is no second copy to forget."

### Beat 3 — The schema assertion (2:55)

*Click the **Tests** tab. Scroll or search to `matches TriageApiResponse schema`.*

> "Here's the contract test. The collection-level pre-request script — separate from the per-request one — fetched `/openapi.json` once at the start of the run and cached the schemas. This assertion pulls `TriageApiResponse` from the cache, compiles it with AJV, and validates the response body.
>
> The consequence: if a developer adds a required field to a Pydantic model in `web/schemas.py`, the OpenAPI document changes on the next server start, and this test picks up the change automatically. The test doesn't need to be edited. The test breaks because the contract changed."

### Beat 4 — Send (3:05)

*Click **Send**.*

> "Eight green checks. Status 200, `execution_mode` is `demo`, `fixture_id` is non-empty, schema validates, severity is a known band, score is between zero and one, timings are present, `case_id` round-trips from the request to the response. Schema validation is doing most of the work; the others are sanity checks that confirm mode precedence is intact and the response shape is what every consumer expects."

### Beat 5 — The fixture-miss proof (3:10)

*Click the `CVE — fixture miss` request. Click **Send**.*

> "Same demo mode. I'm posting a real CVE. There is no `cve__*.json` or `default__cve.json` file in `fixtures/demo/`. This is deliberate.
>
> The server classifies the IOC as a CVE, looks for two fixture keys, finds neither, and raises `503 DEMO_FIXTURE_MISSING`. The error envelope carries a code, a human-readable message, and a `details` object listing the keys it checked. Same envelope shape as every other error in the API.
>
> This is the mode-precedence assertion. Demo mode is not allowed to degrade to live mode. A real-world CVE will not silently trigger a call to NIST NVD on the audience's behalf. The 503 is the contract."

This is the most important beat. Pause for a half-second after delivering it. Let the implication land.

### Beat 6 — The Runner, optional (3:18)

*Click the **Runner** icon. Select the collection. Click **Run**.*

> "Same collection, Postman's GUI runner. Five folders, thirty-seven assertions, green, about a second. Exactly what `newman run` does in CI."

Alt-tab back to the deck. Advance to slide 5.

---

## Slide 5 — Problems prevented (3:20 → 3:45)

### Narration with technical depth

> "Every row is a failure mode test suites hit eventually. Two worth calling out from a systems perspective."

**Tests drift from the code.**

> "Hand-written schemas drift because they require discipline to keep in sync. The schemas in this suite come from `/openapi.json` at runtime — FastAPI emits the document from Pydantic v2 models, no human in the loop. The schema check is impossible to leave stale without also breaking the server. The discipline is structural, not procedural."

**Performance regressions reach production.**

> "Every Postman request has a `pm.expect(pm.response.responseTime).to.be.below(N)` assertion. Per-folder budgets: liveness 200 milliseconds, examples 300, triage 500. A response that is correct but slow fails the build. The CI gate doesn't distinguish between functional regressions and performance regressions — both block the merge."

### Where humans still come in

> "These patterns reduce the human role; they don't eliminate it. A failed contract assertion still needs a human to decide: was this an intended change or a regression? A blown latency budget still needs a human to decide: rerun, investigate, or accept the new baseline. The automation surfaces the question. Humans answer it."

**Transition.** *"One thing to take away."*

---

## Slide 6 — Close (3:45 → 4:00)

### What's on screen

Two columns. Left: three commands to reproduce locally. Right: repo links — the runbook, the API reference, the collection JSON, the CI workflow YAML.

### Narration

> "Same Postman collection. Three checkpoints. Zero drift.
>
> If you want to verify what I showed you — three commands on the left, sixty seconds end to end, no API keys because demo mode runs from local fixtures.
>
> The repo links on the right cover the runbook, the API reference, the collection JSON, and the CI workflow YAML. Everything you saw is reproducible.
>
> Questions to me directly."

---

## Technical FAQ — for the questions that come

### Q: How does demo mode prevent live API calls?

The execution mode is resolved in exactly one place: `web/app.py::triage_api`. When `FLOWRUN_DEMO_MODE=true`, the function short-circuits to `web/demo_mode.py::load_demo_result` and never reaches the LangGraph dispatcher. A missing fixture raises `FileNotFoundError`, which the handler converts to a structured `503 DEMO_FIXTURE_MISSING`. There is no code path from demo mode to a live integration. The CVE fixture-miss test enforces this.

### Q: What happens when the OpenAPI document changes?

Pydantic model change → server restart → new `/openapi.json` → next collection run fetches it → AJV recompiles `TriageApiResponse` → existing assertions either continue passing (non-breaking change) or fail (breaking change). The failure is the signal. The human decides whether the breakage was intentional.

### Q: How does CI actually block merges?

The Postman job is referenced in GitHub's branch protection rules as a required status check. If the job exits non-zero, the pull request cannot be merged without an admin override. The job exits non-zero when (a) the health latency check fails, (b) `jq` finds fewer than 25 total assertions, or (c) `jq` finds any failed assertions. Two of those three conditions are sanity checks on the suite itself — preventing the suite from being silently neutered.

### Q: Where do test results go?

Four destinations, all in `artifacts/postman/`:

| File | Consumer | Purpose |
|---|---|---|
| `newman-report.json` | `jq`, CI gate, downstream dashboards | Machine-readable for gating logic |
| `newman-junit.xml` | GitHub Actions test viewer | Per-assertion rendering inline in pull requests |
| `newman-report.html` | Humans during incident review | Request/response bodies for every failed assertion |
| `newman-cli-summary.txt` | Logs, archives | The boxed terminal output captured |

GitHub Actions uploads all four with `if: always()`, so debugging data exists whether the run passed or failed.

### Q: What about live-mode testing?

Same collection, different environment file. `postman_environment.local.json` sets `expectedExecutionMode=live`. Schema assertions still pass — response shape is identical across modes. Mode-precedence assertions verify `execution_mode: "live"` and `fixture_id: null`. Live runs are not part of the CI gate; they're for manual smoke testing against a real backend when API keys are configured. The reason: vendor rate limits and outages don't belong in a build pipeline.

### Q: When does a human have to step in?

| Trigger | Human action |
|---|---|
| CI gate fails on a pull request | Review JUnit and HTML reports; decide: fix code, fix tests, or revert |
| Pre-commit fails locally | Fix immediately, or `--no-verify` and explain in the PR description |
| Schema assertion fails | Decide if the model change was intentional; update consumers |
| Latency budget fails | Investigate; either fix performance or rebaseline the budget |
| Mode-precedence assertion fails | High-priority — demo mode is leaking; investigate immediately |
| Negative-path assertion fails | Error envelope changed; coordinate with API consumers |
| Live triage returns CRITICAL severity in production | LangGraph escalation gate fires; an analyst confirms before action |

The last row is the only place a human is structurally required during runtime, not just at review time. Everything above the line is humans reviewing automation output asynchronously.

---

## Cross-references

- [`POSTMAN_DEMO_INSTRUCTIONS.md`](POSTMAN_DEMO_INSTRUCTIONS.md) — the click-and-type runbook to hold open during the demo
- [`POSTMAN_SETUP.md`](POSTMAN_SETUP.md) — first-time setup, from clean machine to a green run
- [`../docs/API.md`](../docs/API.md) — endpoint reference and error codes
- `FlowRun_Postman_Demo.pptx` — the deck (slide notes carry tight Presenter View prompts)
- `postman_collection.json` — the collection
- `.github/workflows/postman.yml` — the CI pipeline
