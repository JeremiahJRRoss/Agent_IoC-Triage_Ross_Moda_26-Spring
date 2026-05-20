from __future__ import annotations

import json
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures" / "demo"


def _key(ioc: str) -> str:
    return ioc.strip().lower().replace(":", "_").replace("/", "_")


def load_demo_result(ioc: str) -> tuple[dict, str]:
    canonical = _key(ioc)
    path = FIXTURE_DIR / f"{canonical}.json"
    if not path.exists():
        path = FIXTURE_DIR / "default.json"
        if not path.exists():
            raise FileNotFoundError(f"demo fixture missing for '{ioc}'")
        return json.loads(path.read_text()), "default"
    return json.loads(path.read_text()), canonical
