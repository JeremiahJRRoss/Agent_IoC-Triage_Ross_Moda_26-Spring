# Postman Demo Expectations

## Enrichment timeout/deadline behavior

The triage API is designed to return **partial results** when non-critical enrichment sources are slow or unavailable.

- Each enrichment source call has a per-source timeout (`FLOWRUN_ENRICHMENT_SOURCE_TIMEOUT_S`, default `4.0s`).
- The full enrichment fan-out has an overall deadline (`FLOWRUN_ENRICHMENT_DEADLINE_S`, default `8.0s`).
- If one or more sources time out, triage does **not** hard-fail. The response returns successfully with partial intel.

## Response metadata for monitor assertions

Monitors should validate availability using metadata fields rather than requiring all sources to succeed:

- `timings.total_ms`: End-to-end API processing time in milliseconds.
- `source_summary.available_sources`: Sources that returned usable data.
- `source_summary.failed_sources`: Sources that failed or timed out.
- `warnings[]` (optional): Human-readable non-fatal warnings (for example, timed-out sources or partial enrichment).

## Suggested monitor checks

1. Assert HTTP status is `200` for known-valid IOC payloads.
2. Assert `timings.total_ms` exists and is a non-negative integer.
3. Assert `source_summary.available_sources` is present (may be partial).
4. Allow `source_summary.failed_sources` to be non-empty during upstream incidents.
5. Treat `warnings[]` as diagnostic signal, not a hard failure trigger.

This lets operations monitor agent availability and degraded mode behavior independently from upstream intelligence provider uptime.
