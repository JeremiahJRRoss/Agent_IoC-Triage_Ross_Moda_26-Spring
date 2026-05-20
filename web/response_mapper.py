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


def to_api_response(
    result: dict,
    request: TriageApiRequest,
    *,
    execution_mode: ExecutionMode = ExecutionMode.live,
    fixture_id: str | None = None,
) -> TriageApiResponse:
    severity = SeverityBand(result.get("severity_band", "LOW").upper())
    score = max(0.0, min(1.0, float(result.get("composite_score", 0.0))))

    raw_ioc = result.get("ioc_raw", request.ioc)
    inferred_type = _regex_classify(request.ioc.strip()) or "unknown"
    ioc_type = result.get("ioc_type") or inferred_type
    clean_ioc = result.get("ioc_clean") or _normalise_ioc(request.ioc.strip(), ioc_type)

    return TriageApiResponse(
        case_id=request.case_id,
        ioc=IocIdentity(
            raw=raw_ioc,
            clean=clean_ioc,
            type=ioc_type,
        ),
        verdict=Verdict(
            severity=severity,
            score=score,
            escalation_required=bool(result.get("escalation_required", False)),
            justification=result.get("verdict_justification", "No justification provided."),
        ),
        recommended_actions=_recommended_actions(severity),
        source_summary=SourceSummary(
            available_sources=sorted(list((result.get("raw_intel") or {}).keys())),
            failed_sources=_failed_sources(result.get("intel_errors", [])),
        ),
        score_breakdown=result.get("score_breakdown", {}),
        raw_intel=result.get("raw_intel") if request.include_raw_intel else None,
        report_html=result.get("report_html") if request.include_html_report else None,
        trace=TraceInfo(trace_endpoint=result.get("trace_endpoint")),
        execution_mode=execution_mode,
        fixture_id=fixture_id,
    )
