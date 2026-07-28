# Ross Moda IoC Triage API — Demo Slide Notes

Use these text-only slide notes alongside `POSTMAN_DEMO_SCRIPT.md` and
`POSTMAN_DEMO_INSTRUCTIONS.md`. They replace the prior binary presentation so
pull requests stay source-reviewable.

## Slide 1 — Title

**Ross Moda IoC Triage API**  
Contract testing with Postman

Presenter cue: introduce the agent as a LangGraph-powered IoC triage service for
Jeremiah's Ross Moda portfolio.

## Slide 2 — What the Demo Proves

- Liveness: the service boots and exposes `/health`.
- Contract: responses conform to the OpenAPI-derived schemas.
- Behavior: demo fixtures and live responses share the same public shape.
- Negative paths: empty input and missing fixtures fail with structured errors.

## Slide 3 — Tooling

- Postman collection for local verification.
- Newman for command-line parity with CI.
- GitHub Actions for push and pull-request gating.

## Slide 4 — Live Walkthrough Holding Slide

Leave this slide projected while running the Postman collection.

Checklist:

1. Confirm the demo environment is selected.
2. Run `/health`.
3. Send the default triage request.
4. Run the full collection.
5. Show the assertion count and zero failures.

## Slide 5 — CI Gate

The same collection runs in CI, captures JSON/JUnit/HTML reports, and fails the
build on any contract regression.

## Slide 6 — Takeaways

- Deterministic demo mode makes the testing pattern reproducible.
- The public API contract is checked from the generated schema.
- The same validation path works locally, before push, and in CI.
