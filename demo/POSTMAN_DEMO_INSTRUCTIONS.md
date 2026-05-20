# Postman Demo — Technical Instructions

Click-and-type runbook for the FlowRun IoC Triage Postman demo.
Narration lives in slide notes (Presenter View) — this file is mechanics only.

---

## Setup

Run before the demo. Leave running. Works identically with Docker or
Podman — substitute `podman` for `docker` in every command below.

```bash
# Terminal 1 — build the image (first run only), then start the API in demo mode
docker build -t flowrun-streamlet-ioc-triage:0.0.33 .
docker run -d --name flowrun-demo -p 127.0.0.1:7777:7777 \
  -e FLOWRUN_DEMO_MODE=true -e FLOWRUN_NO_PROMPT=1 \
  flowrun-streamlet-ioc-triage:0.0.33

# Terminal 2 — verify
curl -s http://127.0.0.1:7777/health
# expect: {"status":"ok",...}
```

Demo mode serves every response from local fixtures baked into the image —
no `.env` file and no API keys are needed.

Postman:
- Import `postman_collection.json`
- Top-right environment dropdown → `FlowRun IoC Triage — Demo`
- Expand collection tree (all 5 folders visible)

Deck:
- Open `FlowRun_Postman_Demo.pptx` on slide 1
- Presenter View if available

---

## Slide-by-slide actions

### Slide 1 → 2 → 3 → 4
Advance the deck. No clicks needed in any external app.

### After Slide 4
**Do not advance the deck.** Alt-tab to Postman. Slide 4 stays on screen behind Postman during the live demo.

---

## Live demo in Postman

Six beats. Each one is a click sequence.

### Beat 1 — Show the collection

1. Click the collection name in left nav → tree expands to show 5 folders
2. Point to environment dropdown (top-right) — should read `FlowRun IoC Triage — Demo`

### Beat 2 — Open the example-chain request

1. Click folder `02 — Triage (demo mode)`
2. Click request `POST /api/v1/triage (domain via example chain)`
3. Click the **Pre-request Script** tab

### Beat 3 — Show the schema assertion

1. Click the **Tests** tab
2. Scroll (or Cmd+F → "schema") to the `matches TriageApiResponse schema` block

### Beat 4 — Send the request

1. Click **Send**
2. Response pane auto-opens to **Test Results** tab — green checks visible

### Beat 5 — Fixture-miss proof

1. Click request `CVE — fixture miss` (same folder)
2. Click **Send**
3. Status code: **503**
4. Response body shows error code: `DEMO_FIXTURE_MISSING`

### Beat 6 — Run the suite *(optional, cut first if short on time)*

1. Click **Runner** icon (paper-plane, left sidebar)
2. Select the full collection
3. Click **Run**
4. Wait for green summary

### After demo
Alt-tab back to deck. Advance to slide 5.

---

## Slide 5 → 6
Advance. No external clicks.

---

## Teardown

After the demo, remove the container:
```bash
docker rm -f flowrun-demo
```

---

## Recovery

### Postman frozen / unresponsive
Alt-tab to Terminal 2. Run:
```bash
newman run postman_collection.json -e postman_environment.demo.json
```
Resume on the green summary line.

### Server connection refused
Recreate the container in Terminal 1, then verify:
```bash
docker rm -f flowrun-demo
docker run -d --name flowrun-demo -p 127.0.0.1:7777:7777 \
  -e FLOWRUN_DEMO_MODE=true -e FLOWRUN_NO_PROMPT=1 \
  flowrun-streamlet-ioc-triage:0.0.33
curl -s http://127.0.0.1:7777/health
```

### Wrong environment showing in responses
Top-right dropdown → re-select `FlowRun IoC Triage — Demo`. Re-Send.

### Want to verify full suite passes mid-demo
```bash
./scripts/postman.sh smoke
```

---

## Quick reference

```
Slide 1 → 2 → 3 → 4               (advance only)
After Slide 4 → ALT-TAB to Postman, leave deck on slide 4

Postman:
  Beat 1: click collection → confirm 5 folders + demo env
  Beat 2: 02 folder → "domain via example chain" → Pre-request Script tab
  Beat 3: Tests tab → find "schema"
  Beat 4: Send → green checks
  Beat 5: "CVE — fixture miss" → Send → 503 / DEMO_FIXTURE_MISSING
  Beat 6: Runner → Run full collection  [OPTIONAL]

ALT-TAB to deck → Slide 5 → 6
```
