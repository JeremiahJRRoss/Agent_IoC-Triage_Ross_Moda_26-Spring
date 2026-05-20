from __future__ import annotations

from agent.graph import _normalise_ioc, _regex_classify

from web.schemas import (
    ExecutionMode,
    IocIdentity,
    SeverityBand,
    SourceSummary,
    TraceInfo,
    TriageApiRequest,
    TriageApiResponse,
    Timings,
    Verdict,
)


def _recommended_actions(severity: SeverityBand) -> list[str]:
    if severity in (SeverityBand.HIGH, SeverityBand.CRITICAL):
        return [
            "Block or monitor IOC based on policy.",
            "Search related telemetry across DNS, proxy, and EDR.",
            "Escalate to incident response if internal hits are observed.",
        ]
    return [
        "Continue monitoring for changes in IOC behavior.",
        "Correlate with local telemetry before taking containment action.",
    ]


def _failed_sources(intel_errors: list[str]) -> list[str]:
    out: list[str] = []
    for item in intel_errors:
        out.append(item.split(":", 1)[0])
    return out


def _to_float_or_default(value: object, *, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: object) -> float:
    return max(0.0, min(1.0, _to_float_or_default(value, default=0.0)))


def _normalize_severity(value: object) -> SeverityBand:
    if isinstance(value, SeverityBand):
        return value
    raw = str(value).strip().upper() if value is not None else ""
    return SeverityBand(raw) if raw in SeverityBand._value2member_map_ else SeverityBand.LOW


def _map_state_to_public_fields(result: dict, request: TriageApiRequest) -> dict:
    """Adapter: map internal agent state keys to public API DTO fields only."""
    severity = _normalize_severity(result.get("severity_band"))
    score = _clamp_score(result.get("composite_score"))

    raw_ioc = result.get("ioc_raw", request.ioc)
    inferred_type = _regex_classify(request.ioc.strip()) or "unknown"
    ioc_type = result.get("ioc_type") or inferred_type
    clean_ioc = result.get("ioc_clean") or _normalise_ioc(request.ioc.strip(), ioc_type)

    score_breakdown_raw = result.get("score_breakdown") or {}
    score_breakdown = {
        str(k): _to_float_or_default(v, default=0.0) for k, v in score_breakdown_raw.items()
    }

    return {
        "case_id": request.case_id,
        "ioc": IocIdentity(raw=raw_ioc, clean=clean_ioc, type=ioc_type),
        "verdict": Verdict(
            severity=severity,
            score=score,
            escalation_required=bool(result.get("escalation_required", False)),
            justification=result.get("verdict_justification", "No justification provided."),
        ),
        "recommended_actions": _recommended_actions(severity),
        "source_summary": SourceSummary(
            available_sources=sorted(list((result.get("raw_intel") or {}).keys())),
            failed_sources=_failed_sources(result.get("intel_errors", [])),
        ),
        "score_breakdown": score_breakdown,
        "raw_intel": result.get("raw_intel") if request.include_raw_intel else None,
        "report_html": result.get("report_html") if request.include_html_report else None,
        "trace": TraceInfo(trace_endpoint=result.get("trace_endpoint")),
    }


def to_api_response(
    result: dict,
    request: TriageApiRequest,
    *,
    execution_mode: ExecutionMode = ExecutionMode.live,
    fixture_id: str | None = None,
) -> TriageApiResponse:
    payload = _map_state_to_public_fields(result, request)
    total_ms = int(_to_float_or_default(result.get("total_ms"), default=0.0))
    warnings = result.get("warnings") or None
    return TriageApiResponse(
        **payload,
        timings=Timings(total_ms=max(0, total_ms)),
        warnings=warnings,
        execution_mode=execution_mode,
        fixture_id=fixture_id,
    )
