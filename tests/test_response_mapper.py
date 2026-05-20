from web.response_mapper import _map_state_to_public_fields, to_api_response
from web.schemas import SeverityBand, TriageApiRequest


def test_mapper_normalizes_missing_numeric_values_and_severity_case():
    request = TriageApiRequest(ioc="8.8.8.8", case_id="CASE-1")
    result = {
        "severity_band": "critical",
        "composite_score": None,
        "score_breakdown": {"vt": None, "otx": "0.7"},
        "raw_intel": {"vt": {"hits": 1}},
    }

    mapped = _map_state_to_public_fields(result, request)

    assert mapped["verdict"].severity == SeverityBand.CRITICAL
    assert mapped["verdict"].score == 0.0
    assert mapped["score_breakdown"] == {"vt": 0.0, "otx": 0.7}


def test_mapper_clamps_score_to_contract_range():
    request = TriageApiRequest(ioc="8.8.8.8")

    high = _map_state_to_public_fields({"composite_score": 4.2}, request)
    low = _map_state_to_public_fields({"composite_score": -0.25}, request)

    assert high["verdict"].score == 1.0
    assert low["verdict"].score == 0.0


def test_to_api_response_exposes_only_dto_shape():
    request = TriageApiRequest(ioc="8.8.8.8", include_raw_intel=False, include_html_report=False)
    result = {
        "severity_band": "MeDiuM",
        "composite_score": "0.5",
        "active_weights": {"private": 1.0},
        "ioc_raw": "8.8.8.8",
    }

    response = to_api_response(result, request)
    dumped = response.model_dump()

    assert "active_weights" not in dumped
    assert dumped["verdict"]["severity"] == "MEDIUM"
    assert dumped["verdict"]["score"] == 0.5
