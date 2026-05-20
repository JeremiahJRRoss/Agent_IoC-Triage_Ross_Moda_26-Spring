# web/app.py
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI web interface for FlowRun Streamlet: IoC Triage.
#
# Default deployment surface. Listens on port 7777, serves a minimal htmx UI
# at GET /, accepts IOC submissions at POST /triage, and exposes GET /health
# for container liveness probes.
#
# The agent graph is compiled once at startup; per-request work is just
# graph.ainvoke().
# ─────────────────────────────────────────────────────────────────────────────

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter

import json
import os
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from agent import credentials as _credentials
from agent import graph as _graph
from agent import tracing as _tracing

from web.demo_mode import load_demo_result, load_mock_result
from web.response_mapper import to_api_response
from web.schemas import ApiErrorResponse, ErrorInfo, ExampleApiResponse, ExampleType, ExecutionMode, TriageApiRequest, TriageApiResponse

_WEB_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(_WEB_DIR / "templates"))

_runtime: dict = {}


def _error_response(status: int, code: str, message: str, case_id: str | None = None, details: dict | None = None):
    payload = ApiErrorResponse(
        error=ErrorInfo(code=code, message=message, details=details),
        case_id=case_id,
        trace={"trace_endpoint": _runtime.get("trace_endpoint")},
    ).model_dump()
    return JSONResponse(payload, status_code=status)


def _example_payload(example_type: ExampleType) -> TriageApiRequest:
    example_path = _WEB_DIR.parent / "fixtures" / "examples" / f"{example_type.value}.json"
    if not example_path.exists():
        raise FileNotFoundError(example_type.value)
    payload = json.loads(example_path.read_text())
    return TriageApiRequest.model_validate(payload)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Resolve via module attribute access so test fixtures can monkeypatch the
    # underlying agent.credentials / agent.tracing / agent.graph names.
    _credentials.resolve_credentials()
    _runtime["trace_endpoint"] = _tracing.init_tracing()
    _runtime["graph"] = _graph.build_graph()
    yield


_API_DESCRIPTION = """\
FlowRun Streamlet automated IoC triage API.

Submit an indicator of compromise (IP, domain, URL, file hash, CVE, or
software package) and receive a structured threat verdict with a weighted
composite score, a severity band, and recommended actions.

### Execution modes

The API resolves exactly one execution mode per request. Precedence is
strict and decided server-side — clients never choose the mode directly:

1. **demo** — when `FLOWRUN_DEMO_MODE=true`, `POST /api/v1/triage` serves
   deterministic fixtures only and never calls live threat-intel APIs. A
   missing fixture is a hard `503 DEMO_FIXTURE_MISSING`, never a silent
   fallthrough to live mode.
2. **mock** — `POST /api/v1/triage/mock` always returns the canned
   `fixtures/demo/mock.json` payload, independent of the environment. Use it
   for schema-only contract checks.
3. **live** — the default. `POST /api/v1/triage` runs the real LangGraph
   agent against the configured threat-intel integrations.

Every triage response carries `execution_mode` and (for demo/mock)
`fixture_id`, so clients can assert which path produced the result.

See `docs/API.md` for the full reference.
"""

_OPENAPI_TAGS = [
    {"name": "Liveness", "description": "Container health and readiness probes."},
    {"name": "UI", "description": "Browser-facing htmx triage interface."},
    {"name": "Examples", "description": "Canonical sample triage payloads sourced from fixtures/examples."},
    {"name": "Triage", "description": "IoC triage endpoints across the live, demo, and mock execution modes."},
]

app = FastAPI(
    title="FlowRun Streamlet: IoC Triage",
    description=_API_DESCRIPTION,
    version="0.0.33",
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
)
app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")


@app.get(
    "/health",
    tags=["Liveness"],
    summary="Liveness probe",
    description=(
        "Returns service status and the active OpenTelemetry trace endpoint.\n\n"
        "Used by container orchestrators as a liveness/readiness probe. Always\n"
        "cheap: performs no agent work and makes no external calls."
    ),
)
async def health():
    return {
        "status": "ok",
        "trace_endpoint": _runtime.get("trace_endpoint"),
    }


@app.get(
    "/",
    response_class=HTMLResponse,
    tags=["UI"],
    summary="Triage web UI",
    description="Serves the minimal htmx-driven single-page triage form.",
)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"trace_endpoint": _runtime.get("trace_endpoint") or "(tracing disabled)"},
    )


@app.post(
    "/triage",
    response_class=HTMLResponse,
    tags=["UI"],
    summary="Submit an IOC from the web UI",
    description=(
        "Form-encoded triage submission used by the htmx UI. Returns an HTML\n"
        "report fragment for inline rendering. For programmatic access use\n"
        "POST /api/v1/triage, which returns structured JSON instead."
    ),
    responses={
        400: {"description": "Empty IOC submitted.", "content": {"text/html": {}}},
        500: {"description": "Triage execution failed.", "content": {"text/html": {}}},
        503: {"description": "Agent not initialised.", "content": {"text/html": {}}},
    },
)
async def triage(ioc: str = Form(...)):
    ioc = (ioc or "").strip()
    if not ioc:
        return PlainTextResponse(
            '<p style="color:#dc2626;">Please enter an IOC.</p>',
            status_code=400,
        )

    graph = _runtime.get("graph")
    if graph is None:
        return PlainTextResponse(
            '<p style="color:#dc2626;">Agent not initialised.</p>',
            status_code=503,
        )

    try:
        result = await graph.ainvoke({"ioc_raw": ioc})
    except SystemExit as exc:
        return HTMLResponse(
            f'<p style="color:#f59e0b;">⚠️ {exc}</p>',
            status_code=200,
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f'<p style="color:#dc2626;">❌ Triage failed: '
            f'{type(exc).__name__}: {exc}</p>',
            status_code=500,
        )

    return result.get(
        "report_html",
        '<p style="color:#dc2626;">No report generated.</p>',
    )


@app.get(
    "/api/v1/examples/{example_type}",
    response_model=ExampleApiResponse,
    tags=["Examples"],
    summary="Fetch a canonical example payload",
    description=(
        "Returns a ready-to-POST triage request body for the given IOC type,\n"
        "sourced from fixtures/examples/*.json. This is the single source of\n"
        "truth for sample payloads — Postman requests and docs chain off it\n"
        "rather than hand-coding JSON."
    ),
    responses={
        404: {
            "model": ApiErrorResponse,
            "description": "Unknown IOC type or missing example fixture (EXAMPLE_NOT_FOUND).",
        },
        500: {
            "model": ApiErrorResponse,
            "description": "Example fixture failed schema validation (EXAMPLE_INVALID).",
        },
    },
)
async def triage_example(example_type: str):
    try:
        parsed_type = ExampleType(example_type)
    except ValueError:
        return _error_response(404, "EXAMPLE_NOT_FOUND", "Example type not found", details={"example_type": example_type})

    try:
        payload = _example_payload(parsed_type)
    except FileNotFoundError:
        return _error_response(404, "EXAMPLE_NOT_FOUND", "Example type not found", details={"example_type": example_type})
    except ValueError as exc:
        return _error_response(500, "EXAMPLE_INVALID", f"Invalid example fixture: {exc}", details={"example_type": example_type})
    return {"type": parsed_type, "payload": payload, "notes": None}


@app.post(
    "/api/v1/triage",
    response_model=TriageApiResponse,
    tags=["Triage"],
    summary="Triage an IOC",
    description=(
        "Runs IoC triage and returns a structured verdict.\n\n"
        "Behavior depends on the resolved execution mode: with\n"
        "FLOWRUN_DEMO_MODE=true the response is served from a deterministic\n"
        "fixture (execution_mode=demo) and a missing fixture is a hard 503;\n"
        "otherwise the live LangGraph agent runs (execution_mode=live)."
    ),
    responses={
        400: {
            "model": ApiErrorResponse,
            "description": "IOC was empty (IOC_EMPTY).",
        },
        500: {
            "model": ApiErrorResponse,
            "description": "Live triage raised an unexpected error (TRIAGE_FAILED).",
        },
        503: {
            "model": ApiErrorResponse,
            "description": "Demo fixture missing (DEMO_FIXTURE_MISSING) or agent not initialised (AGENT_UNAVAILABLE).",
        },
    },
)
async def triage_api(request: TriageApiRequest):
    ioc = request.ioc.strip()
    if not ioc:
        return _error_response(400, "IOC_EMPTY", "IOC must not be empty", case_id=request.case_id)

    # Execution mode precedence:
    # 1) FLOWRUN_DEMO_MODE=true => fixtures only (never live integrations)
    # 2) /api/v1/triage/mock => canned fixture response only
    # 3) default / live => real integrations
    demo_mode = os.getenv("FLOWRUN_DEMO_MODE", "false").lower() == "true"
    if demo_mode:
        try:
            result, fixture_id = load_demo_result(ioc)
        except FileNotFoundError as exc:
            return _error_response(503, "DEMO_FIXTURE_MISSING", str(exc), case_id=request.case_id)
        return to_api_response(result, request, execution_mode=ExecutionMode.demo, fixture_id=fixture_id)

    graph = _runtime.get("graph")
    if graph is None:
        return _error_response(503, "AGENT_UNAVAILABLE", "Agent not initialised.", case_id=request.case_id)

    try:
        started = perf_counter()
        result = await graph.ainvoke({"ioc_raw": ioc})
        result["total_ms"] = int((perf_counter() - started) * 1000)
        return to_api_response(result, request, execution_mode=ExecutionMode.live)
    except Exception as exc:  # noqa: BLE001
        return _error_response(500, "TRIAGE_FAILED", f"{type(exc).__name__}: {exc}", case_id=request.case_id)


@app.post(
    "/api/v1/triage/mock",
    response_model=TriageApiResponse,
    tags=["Triage"],
    summary="Triage against the mock fixture",
    description=(
        "Always returns the canned fixtures/demo/mock.json payload with\n"
        "execution_mode=mock and fixture_id=mock. Independent of\n"
        "FLOWRUN_DEMO_MODE — use it for schema and contract checks that must\n"
        "not depend on per-IOC fixtures."
    ),
    responses={
        503: {
            "model": ApiErrorResponse,
            "description": "Mock fixture missing (MOCK_FIXTURE_MISSING).",
        },
    },
)
async def triage_api_mock(request: TriageApiRequest):
    try:
        result, fixture_id = load_mock_result()
    except FileNotFoundError as exc:
        return _error_response(503, "MOCK_FIXTURE_MISSING", str(exc), case_id=request.case_id)
    return to_api_response(result, request, execution_mode=ExecutionMode.mock, fixture_id=fixture_id)
