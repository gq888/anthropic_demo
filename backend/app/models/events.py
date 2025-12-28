"""Event primitives for research run observability."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .enums import EventType

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class RunEvent:
    """Represents a structured event emitted during a research run."""

    run_id: str
    type: EventType
    timestamp: datetime = field(default_factory=_utc_now)
    payload: Dict[str, Any] = field(default_factory=dict)
    agent_id: Optional[str] = None
