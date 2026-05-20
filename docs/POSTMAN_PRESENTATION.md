# Postman Demo — Presenter Script

A standalone 4-minute script for demoing the FlowRun IoC Triage API contract
checks with Postman/Newman. Read this end-to-end once before presenting.

---

## 1. Pre-flight checklist

Do all of this **before** the audience is watching:

- [ ] Terminal A open, repo root, server running in demo mode:
      `FLOWRUN_DEMO_MODE=true FLOWRUN_NO_PROMPT=1 python -m uvicorn web.app:app --host 127.0.0.1 --port 7777`
- [ ] `curl -s http://127.0.0.1:7777/health` returns `{"status":"ok",...}`.
- [ ] Terminal B open, repo root, ready to type — this is the demo terminal.
- [ ] Browser tab open at `http://127.0.0.1:7777/docs` (Swagger UI).
- [ ] Postman app open with `postman_collection.json` imported and the
      `FlowRun IoC Triage — Demo` environment selected.
- [ ] Newman installed: `newman --version` prints a version.
- [ ] **Network-isolation proof staged**: if running in Docker, have
      `docker network disconnect <network> <container>` ready to show that
      demo mode makes zero outbound calls. (No container? Skip — the
      `FLOWRUN_DEMO_MODE` env var alone guarantees fixture-only behavior.)
- [ ] Font size bumped in both terminals and the browser.

---

## 2. Minute-by-minute script

Total: **4:00**. Wall-clock targets are cumulative.

### Frame — 0:45 (→ 0:45)

- **Show:** the Postman collection tree (folders `00`–`04`).
- **Say:** "This API triages indicators of compromise. The hard part isn't
  the happy path — it's proving the *contract* holds and that demo mode never
  leaks a live API call. That's what these 37 assertions check."
- **Click:** expand folder `02 — Triage (demo mode)`.

### Contract — 0:45 (→ 1:30)

- **Show:** the `domain via example chain` request and its Tests tab.
- **Say:** "Every triage response is validated against the `TriageApiResponse`
  schema pulled live from `/openapi.json` — not a hand-written copy. If a field
  type drifts in `web/schemas.py`, this assertion fails."
- **Click:** **Send**; point at the green `matches TriageApiResponse schema`.

### Fixtures as truth — 1:00 (→ 2:30)

- **Show:** `fixtures/demo/default__domain.json` next to the response.
- **Say:** "Demo mode is deterministic. The response is this fixture, byte for
  byte — no model, no network. That's what makes the demo reproducible and
  CI-safe with zero API keys."
- **Click:** in Terminal B, run
  `curl -s -X POST http://127.0.0.1:7777/api/v1/triage -H 'Content-Type: application/json' -d '{"ioc":"malware.wicar.org"}' | jq .execution_mode,.fixture_id`.

### Mode precedence — 0:45 (→ 3:15)

- **Show:** folder `02`, request `CVE — fixture miss`.
- **Say:** "A CVE classifies fine but has no demo fixture. Strict precedence
  means demo mode *hard-fails* with 503 — it never silently degrades to a live
  call. That's the guarantee."
- **Click:** **Send**; show the green `503` + `DEMO_FIXTURE_MISSING` assertions.

### Negatives — 0:30 (→ 3:45)

- **Show:** folder `04 — Negative & contract`.
- **Say:** "Empty IOC is a structured 400, not a stack trace. `case_id` round-
  trips verbatim so a SOC can correlate results."
- **Click:** **Run folder** `04`; show both requests green.

### CI parity — 0:15 (→ 4:00)

- **Show:** Terminal B.
- **Say:** "Same collection, same environment file, runs in CI on every push."
- **Click:** `./scripts/postman.sh smoke` — let the green summary land.

---

## 3. Cut order

If running long, drop in this order (highest priority to cut first):

1. **The network-isolation proof** (`docker network disconnect`) — the env var
   already guarantees it; the visual is nice-to-have.
2. **The Terminal B curl** in "Fixtures as truth" — the Postman response
   already shows `execution_mode`/`fixture_id`.
3. **The CI parity block** — mention it verbally instead of running the script.

---

## 4. Backup pocket

If the live Postman UI misbehaves (rendering, environment not selected,
freeze), fall back to the terminal — it never fails:

```bash
newman run postman_collection.json -e postman_environment.demo.json | tee /tmp/demo.txt
```

Talk over the scrolling output; the boxed summary at the end gives you the
same 37-assertions / 0-failed headline. If the *server* is down, restart it
with the Pre-flight command and run `./scripts/postman.sh smoke` to recover.

---

## 5. FAQ

**Q: Does demo mode ever call the real threat-intel APIs?**
A: No. `FLOWRUN_DEMO_MODE=true` routes `POST /api/v1/triage` entirely through
`fixtures/demo/` lookups. A missing fixture is a 503 — there is no code path
from demo mode to a live integration.

**Q: How is the schema assertion kept in sync with the code?**
A: It isn't a copy. The collection fetches `/openapi.json` once per run and
validates responses against `components.schemas.TriageApiResponse`. The schema
is generated from `web/schemas.py`, so the test tracks the code automatically.

**Q: Why is a CVE used as the negative case instead of garbage input?**
A: Garbage tests validation. A CVE is *valid and correctly classified* — it
just has no demo fixture. That specifically proves mode precedence is strict:
a real, well-formed IOC still hard-fails rather than falling through to live.
