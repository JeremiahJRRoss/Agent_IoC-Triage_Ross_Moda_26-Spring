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
from web.schemas import ApiErrorResponse, ErrorInfo, ExecutionMode, TriageApiRequest, TriageApiResponse

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


def _example_payload(example_type: str) -> dict:
    example_path = _WEB_DIR.parent / "fixtures" / "examples" / f"{example_type}.json"
    if not example_path.exists():
        raise FileNotFoundError(example_type)
    return json.loads(example_path.read_text())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Resolve via module attribute access so test fixtures can monkeypatch the
    # underlying agent.credentials / agent.tracing / agent.graph names.
    _credentials.resolve_credentials()
    _runtime["trace_endpoint"] = _tracing.init_tracing()
    _runtime["graph"] = _graph.build_graph()
    yield


app = FastAPI(title="FlowRun Streamlet: IoC Triage", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(_WEB_DIR / "static")), name="static")


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "trace_endpoint": _runtime.get("trace_endpoint"),
    }


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        request,
        "index.html",
        {"trace_endpoint": _runtime.get("trace_endpoint") or "(tracing disabled)"},
    )


@app.post("/triage", response_class=HTMLResponse)
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


@app.get("/api/v1/examples/{example_type}")
async def triage_example(example_type: str):
    try:
        payload = _example_payload(example_type)
    except FileNotFoundError:
        return _error_response(404, "EXAMPLE_NOT_FOUND", "Example type not found", details={"example_type": example_type})
    return payload


@app.post("/api/v1/triage", response_model=TriageApiResponse)
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
        result = await graph.ainvoke({"ioc_raw": ioc})
        return to_api_response(result, request, execution_mode=ExecutionMode.live)
    except Exception as exc:  # noqa: BLE001
        return _error_response(500, "TRIAGE_FAILED", f"{type(exc).__name__}: {exc}", case_id=request.case_id)


@app.post("/api/v1/triage/mock", response_model=TriageApiResponse)
async def triage_api_mock(request: TriageApiRequest):
    try:
        result, fixture_id = load_mock_result()
    except FileNotFoundError as exc:
        return _error_response(503, "MOCK_FIXTURE_MISSING", str(exc), case_id=request.case_id)
    return to_api_response(result, request, execution_mode=ExecutionMode.mock, fixture_id=fixture_id)
