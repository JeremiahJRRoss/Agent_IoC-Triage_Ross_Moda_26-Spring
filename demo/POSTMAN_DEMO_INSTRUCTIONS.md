# Postman Demo — Live Runbook

Demos fail in predictable ways. The wrong window is in front, the wrong environment is selected, an API key expires on the day you present, a rate limit chooses that moment to kick in. This document is the script for when your hands forget what your slides are saying. Read it once before you present; keep it open in a window you can glance at during.

The whole demo is four minutes. The walkthrough in Postman is sixty seconds of that. The rest is context. This file covers the sixty seconds and the recovery paths for when they go sideways.

---

## Demo mode versus live mode

Before you run anything, understand what you are showing.

The Ross Moda service has two operating modes that share a single Postman collection. Demo mode is the presentation; live mode is the production. Both execute the same thirty-seven assertions against the same schema. What changes is what sits on the other side of the wire.

**Demo mode** (`IOC_TRIAGE_DEMO_MODE=true`) reads triage responses from JSON files baked into the container at `fixtures/demo/*.json`. The LangGraph agent never runs. No outbound call is made to VirusTotal, AbuseIPDB, OTX, urlscan.io, NVD, or OSV.dev. No API key is required. Responses are deterministic to the millisecond — every assertion behaves identically every time. This is what you run on stage, in CI, and on a clean machine. It exists for one reason: the *testing pattern* is the product of this demo, not the threat-intel results, and showing the pattern requires that the wire doesn't surprise you.

**Live mode** is the default and what production uses. The LangGraph agent runs, queries the configured threat-intel APIs in parallel, weights and correlates the responses, and returns a real verdict. Live mode needs five API keys in `.env` and tolerates the realities of free-tier rate limits and occasional vendor outages. Live mode is what the testing pattern is *for*. Demo mode is how you prove the pattern works without depending on any of those vendors during a presentation.

Both modes return the same response shape. The schema assertions pass against either. The only field that differs is `execution_mode`, which carries the value `demo`, `live`, or `mock`, and the collection asserts it equals the value of `expectedExecutionMode` in the active environment. That is what makes the modes provably distinct at the test layer — not by convention, but by contract.

You will present in demo mode. The audience is watching the test infrastructure, not the threat data.

---

## Pre-flight (run thirty minutes before)

You need three things alive when the demo starts: a container, a Postman workspace, and text-only slide notes.

### Container

From the repository root, with Docker running:

```bash
IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
curl -s http://127.0.0.1:7777/health
```

The first command builds the image on first run (≈45 seconds) and reuses the cache afterward (≈3 seconds to start). The second confirms the server is listening. A successful response is `{"status":"ok","trace_endpoint":"…"}`. If `curl` returns anything else, jump to the recovery section before you do anything else — fix this now, not on stage.

Leave the container running. If your machine sleeps between pre-flight and the demo, the container survives the sleep but loses about a second of warm-up cache; bring it back to ready with one curl.

### Postman

Open Postman — desktop app or web client, your choice. Both share state through Postman's cloud, so the workspace you populated during setup is already there. If this is your first time, follow [`POSTMAN_SETUP.md`](POSTMAN_SETUP.md) and come back.

Confirm three things in the Postman window:

1. The collection **Ross Moda IoC Triage API** is visible in the left sidebar with its five folders expanded. Click the chevron next to the collection name if they are collapsed.
2. The environment dropdown in the upper right reads **Ross Moda IoC Triage — Demo**. If it reads anything else, click and switch. This single dropdown is the difference between proving demo mode and proving live mode.
3. The folder `02 — Triage (demo mode)` is expanded so the audience sees the request names when you scroll.

Run the suite once now, with the Collection Runner (opened from the `...` menu on the collection name). Expect thirty-seven green checks in about a second. If anything is red, debug it before the demo, not during.

### Slide notes

Open `POSTMAN_DEMO_SLIDES.md` to slide 1. Keep the slide notes open if you want prompts. The text notes carry tight prompts; this document carries the click sequences.

---

## The shape of the next four minutes

Six beats, in order. Use the slide notes to step through slides 1–4. After slide 4 you alt-tab to Postman and stay there for the six Postman beats. After the Postman beats you alt-tab back and advance to slides 5–6.

The audience never sees you switch environments, edit a request, or open settings. Everything you click is rehearsed and visible. If you are tempted to improvise, do it after the run-through assertion summary appears green — not before.

---

## Slides 1–4 (no clicks in any external app)

Advance the slide notes. Read the notes if you need prompts. These slides exist to give the audience the four pillars (liveness, contract, behavior, negative paths), the three definitions (Postman, collection, Newman), and the three checkpoints (pre-commit, pre-push, CI). They prime everything you are about to show.

**At the end of slide 4, do not advance the slide notes.** Keep the slide 4 notes visible behind Postman during the live walkthrough if you are screen sharing them. Alt-tab to Postman.

---

## The six Postman beats

### Beat 1 — Show the collection (≈10 seconds)

Click the collection name in the left sidebar. The folder tree expands.

The audience sees five folders: `00 — Liveness`, `01 — Examples`, `02 — Triage (demo mode)`, `03 — Triage (mock mode)`, `04 — Negative & contract`. Each folder name maps to one of the four pillars from slide 2. Liveness is the cheapest possible probe — does the server answer? Examples is the fixture endpoint that every triage test chains off. Triage demo mode is the contract test against fixture-backed responses. Triage mock mode is the schema-only check that runs against a canned payload regardless of environment. Negative & contract is the suite of failure modes — empty IOCs, fixture misses, error envelopes.

Point at the environment dropdown in the upper right. Confirm aloud that it reads `Ross Moda IoC Triage — Demo`. This is the moment to mention that the same collection runs against `Ross Moda IoC Triage — Local` for live mode and the assertions still pass — only the value of `expectedExecutionMode` changes.

### Beat 2 — Open the example-chain request (≈10 seconds)

Click folder `02 — Triage (demo mode)`. Click the request `POST /api/v1/triage (domain via example chain)`. Click the **Pre-request Script** tab.

The pre-request script makes one HTTP call to `GET /api/v1/examples/domain`, takes the response's `payload` field, and stores it in a variable named `examplePayload`. The actual request body is the literal string `{{examplePayload}}`. Postman substitutes the variable at send time. The point — say this aloud — is that the same JSON file (`fixtures/examples/domain.json`) is both the API's published example and the test's input. Update one, both update. There is no second copy of the canonical payload to forget about.

### Beat 3 — Show the schema assertion (≈10 seconds)

Click the **Tests** tab. Scroll to the block labeled `matches TriageApiResponse schema`. If the tab is long, use `Cmd-F` or `Ctrl-F` to search for "schema".

The script pulls the cached OpenAPI schemas from a collection variable, compiles `TriageApiResponse` with AJV, and validates the response body. The cache itself is populated once per run by a collection-level pre-request script — you don't need to open that one — which fetches `/openapi.json` from the running server before any request fires. Tell the audience this is the difference between testing what you think the contract is and testing what the server's own schema reports the contract to be. A developer who edits a Pydantic model in `web/schemas.py` doesn't break the test by forgetting to update something — they break it by changing the contract, which is the correct failure.

### Beat 4 — Send the request (≈10 seconds)

Click **Send**.

The response pane opens to the **Test Results** tab and shows eight green checks. Read the assertion list aloud at speed: status 200, `execution_mode` is `demo`, `fixture_id` is non-empty, schema validates, severity is a known band, score is between zero and one, timings are present, `case_id` round-trips. The schema validation is doing the most work; the others are sanity checks that confirm mode precedence is intact and the response shape is what every downstream consumer expects.

### Beat 5 — The fixture-miss proof (≈10 seconds)

Click the request `CVE — fixture miss` in the same folder. Click **Send**.

The response is `503 DEMO_FIXTURE_MISSING`. The body shows a structured error envelope with `error.code`, `error.message`, and `error.details`. There is no `cve__*.json` or `default__cve.json` file in `fixtures/demo/`. This is deliberate. The test asserts that, in demo mode, an IOC type with no fixture must hard-fail with a structured error — never silently fall through to a live API call to NVD. **This single assertion is the proof that demo mode and live mode are provably distinct at runtime.** Without it, demo mode would be a convention; with it, demo mode is a contract.

Spend a beat on this one. It is the most demonstrative assertion in the suite.

### Beat 6 — Optional: run the full suite (≈15 seconds)

Cut this beat first if the previous ones ran long.

Click the **Runner** icon in the left sidebar (paper-plane). Select the collection. Click **Run Ross Moda IoC Triage API**. In about a second you see thirty-seven green checks at the bottom of the runner. This is the Postman-GUI equivalent of `newman run` — same JavaScript sandbox, same assertions, same outcome. The point is that what your laptop just did is exactly what GitHub Actions does on every push.

Alt-tab back to the slide notes. Advance to slide 5.

---

## Slides 5–6 (no clicks in any external app)

Slide 5 covers the failure modes the suite catches. Slide 6 is the close. Advance through them and take questions.

---

## Teardown

After the demo and any questions:

```bash
docker compose down
```

The `.env` file (if you created one for development) stays. The container, image cache, and Docker volumes are removed.

---

## Recovery

These are the four things that go wrong in practice. Read them now; you will not have time to read them during.

### Postman is unresponsive or has frozen

This happens occasionally on laptops with constrained memory. Alt-tab to a terminal and run:

```bash
newman run postman_collection.json -e postman_environment.demo.json
```

Newman is Postman's headless engine. It loads the same collection JSON, runs the same JavaScript sandbox, and emits the same assertions to stdout. You lose the visual but keep the demo. Resume on the green summary line.

### `ECONNREFUSED` or no response from `curl /health`

The container is not running or the port mapping was lost. Recreate it:

```bash
docker compose down
IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
sleep 2
curl -s http://127.0.0.1:7777/health
```

Two seconds is enough for the FastAPI lifespan hook to finish. If `/health` still fails, check Docker Desktop's resource panel — running out of memory is the most common cause of a container that starts and immediately exits.

### Wrong environment selected (`execution_mode` assertion fails)

The dropdown drifted, or you opened a fresh Postman window. Switch to **Ross Moda IoC Triage — Demo** in the upper-right dropdown and re-Send. Do not edit the assertion — the assertion is correct, the environment is wrong.

### All triage requests return `503 DEMO_FIXTURE_MISSING`

The container started without `IOC_TRIAGE_DEMO_MODE=true`. Recreate it with the variable set:

```bash
docker compose down
IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
```

This is the failure mode that proves the testing pattern works — if demo mode is off, demo-mode fixtures are unreachable, and the suite catches it.

---

## Quick reference card

Tear this out (mentally) and keep it visible.

```
Pre-flight:    IOC_TRIAGE_DEMO_MODE=true docker compose up --build -d
               curl -s http://127.0.0.1:7777/health
               Postman → env = "Ross Moda IoC Triage — Demo"
               Slide notes → slide 1

Slides 1 → 2 → 3 → 4              advance only
End of slide 4: ALT-TAB to Postman, leave notes on slide 4

Postman beats:
  1: click collection → confirm 5 folders + Demo environment
  2: 02 folder → "domain via example chain" → Pre-request Script tab
  3: Tests tab → find "schema"
  4: Send → eight green
  5: "CVE — fixture miss" → Send → 503 / DEMO_FIXTURE_MISSING
  6: Runner → Run full collection                          [optional]

ALT-TAB to slide notes → slide 5 → 6 → Q&A

Teardown:      docker compose down
```

For the why behind each beat, see [`POSTMAN_DEMO_SCRIPT.md`](POSTMAN_DEMO_SCRIPT.md). For first-time setup, see [`POSTMAN_SETUP.md`](POSTMAN_SETUP.md). For the API contract every assertion tests against, see [`../docs/API.md`](../docs/API.md).
