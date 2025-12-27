"""Utility to safely parse JSON fragments from LLM outputs."""

from __future__ import annotations

import json
from typing import Any, Dict


def extract_json(payload: str) -> Dict[str, Any]:
    """Attempt to parse JSON from payload; fallback to wrapping raw text."""

    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"report": payload, "citations": []}
