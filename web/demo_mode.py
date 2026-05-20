from __future__ import annotations

import json
from pathlib import Path

from agent.graph import _normalise_ioc, _regex_classify

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo"
MOCK_FIXTURE_PATH = FIXTURE_DIR / "mock.json"


def _normalise_fixture_id(value: str) -> str:
    return value.strip().lower().replace(":", "_").replace("/", "_")


def _fixture_candidates(ioc: str) -> list[tuple[str, Path]]:
    ioc_clean = ioc.strip()
    ioc_type = _regex_classify(ioc_clean) or "unknown"
    canonical_ioc = _normalise_ioc(ioc_clean, ioc_type)

    canonical_key = _normalise_fixture_id(canonical_ioc)
    type_key = _normalise_fixture_id(ioc_type)

    candidates = [
        (f"{type_key}__{canonical_key}", FIXTURE_DIR / f"{type_key}__{canonical_key}.json"),
        (f"default__{type_key}", FIXTURE_DIR / f"default__{type_key}.json"),
    ]
    return candidates


def load_demo_result(ioc: str) -> tuple[dict, str]:
    for fixture_id, path in _fixture_candidates(ioc):
        if path.exists():
            return json.loads(path.read_text()), fixture_id

    checked = [fixture_id for fixture_id, _ in _fixture_candidates(ioc)]
    raise FileNotFoundError(
        f"demo fixture missing for '{ioc}'. Checked: {', '.join(checked)}"
    )


def load_mock_result() -> tuple[dict, str]:
    if not MOCK_FIXTURE_PATH.exists():
        raise FileNotFoundError("mock fixture missing: fixtures/demo/mock.json")
    return json.loads(MOCK_FIXTURE_PATH.read_text()), "mock"
