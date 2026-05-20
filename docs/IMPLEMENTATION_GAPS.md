# Implementation Gaps After API v1 + Demo Mode

This checklist captures what still remains to fully complete the Postman-first implementation plan.

## 1) Contract hardening (high priority)

- [ ] Add complete status-code mapping for API routes (`400/422/429/502/503/500`) and ensure every error path returns the same schema.
- [ ] Add explicit unsupported-IOC error handling (`IOC_UNSUPPORTED`) from graph output (`ioc_type=unknown`).
- [ ] Add Pydantic/OpenAPI examples for success and error responses.

## 2) Deterministic mode semantics

- [ ] Expand fixtures beyond fallback `default.json` to include realistic domain/ip/hash/cve severity scenarios.
- [ ] Document exact fixture lookup precedence and fallback behavior in README + demo docs.
- [ ] Add tests for `FLOWRUN_DEMO_MODE=true`, including fixture hit and missing fixture behavior.

## 3) API validation and tests

- [ ] Add tests for `/api/v1/triage/mock`.
- [ ] Add tests for `include_raw_intel=true` and `include_html_report=true`.
- [ ] Add negative tests for empty IOC, unknown IOC, and graph unavailable on JSON API endpoints.
- [ ] Add mapper-focused unit tests for severity normalization and score clamping.

## 4) Postman deliverables (currently missing)

- [ ] Add collection: `postman/FlowRun IoC Triage API.postman_collection.json`.
- [ ] Add environments: `postman/Local.postman_environment.json`, `postman/Demo.postman_environment.json`.
- [ ] Add collection test scripts for schema shape + severity set + score range.

## 5) CI automation (currently missing)

- [ ] Add CI workflow that runs Postman/Newman collection in deterministic demo mode.
- [ ] Publish artifacts (JUnit + JSON report) from collection run.
- [ ] Add pass/fail quality gate for API assertions.

## 6) Documentation polish

- [ ] Add `docs/POSTMAN_DEMO.md` with step-by-step demo script.
- [ ] Update `README.md` with new JSON endpoints and curl examples.
- [ ] Document `scripts/compose.sh` usage and parity with native compose commands.

## 7) Reliability and observability enhancements

- [ ] Add per-source timeout policy and capture partial-failure warnings in API response metadata.
- [ ] Include optional response timing fields (`total_ms`, per-source timing where available).
- [ ] Add monitor-friendly deterministic request recommendation in docs.
