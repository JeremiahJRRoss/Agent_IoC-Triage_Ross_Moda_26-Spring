from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class SeverityBand(str, Enum):
    CLEAN = "CLEAN"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ExecutionMode(str, Enum):
    live = "live"
    demo = "demo"
    mock = "mock"


class ExampleType(str, Enum):
    domain = "domain"
    ip = "ip"
    hash = "hash"
    cve = "cve"


class TriageApiRequest(BaseModel):
    ioc: str = Field(min_length=1)
    case_id: str | None = None
    source: str = "manual"
    include_raw_intel: bool = False
    include_html_report: bool = False




class ExampleApiResponse(BaseModel):
    type: ExampleType
    payload: TriageApiRequest
    notes: str | None = None


class IocIdentity(BaseModel):
    raw: str
    clean: str
    type: str


class Verdict(BaseModel):
    severity: SeverityBand
    score: float
    escalation_required: bool
    justification: str


class SourceSummary(BaseModel):
    available_sources: list[str]
    failed_sources: list[str]


class TraceInfo(BaseModel):
    trace_endpoint: str | None = None


class Timings(BaseModel):
    total_ms: int = 0


class ErrorInfo(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ApiErrorResponse(BaseModel):
    error: ErrorInfo
    case_id: str | None = None
    trace: TraceInfo | None = None


class TriageApiResponse(BaseModel):
    case_id: str | None = None
    ioc: IocIdentity
    verdict: Verdict
    recommended_actions: list[str]
    source_summary: SourceSummary
    score_breakdown: dict[str, float]
    raw_intel: dict | None = None
    report_html: str | None = None
    trace: TraceInfo
    timings: Timings = Timings()
    warnings: list[str] | None = None
    execution_mode: ExecutionMode = ExecutionMode.live
    fixture_id: str | None = None
