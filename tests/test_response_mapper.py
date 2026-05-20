from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parent.parent))

from web.response_mapper import to_api_response
from web.schemas import ExecutionMode, TriageApiRequest


def test_mapper_clamps_score_and_normalizes_severity():
    result = {
        "ioc_raw": "x",
        "ioc_clean": "x",
        "ioc_type": "domain",
        "severity_band": "high",
        "composite_score": 9.2,
        "raw_intel": {},
        "intel_errors": [],
        "score_breakdown": {},
        "escalation_required": False,
        "verdict_justification": "ok",
        "trace_endpoint": None,
    }
    request = TriageApiRequest(ioc="x")
    response = to_api_response(result, request, execution_mode=ExecutionMode.live)
    assert response.verdict.severity.value == "HIGH"
    assert response.verdict.score == 1.0
