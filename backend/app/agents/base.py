"""Base classes and utilities for agents."""

from __future__ import annotations

import abc
from datetime import datetime
from typing import Any, Optional

from app.llm.client import LLMClient
from app.models.enums import AgentRole, AgentStatus, EventType
from app.models.events import RunEvent
from app.services.run_store import run_store


class BaseAgent(abc.ABC):
    """Abstract base agent providing common utilities."""

    def __init__(self, run_id: str, name: str, role: AgentRole) -> None:
        self.run_id = run_id
        self.name = name
        self.role = role
        self.llm = LLMClient()
        self.agent_id: Optional[str] = None

    async def register(self, brief: Optional[str] = None) -> None:
        agent_state = await run_store.add_agent(self.run_id, self.name, self.role, brief=brief)
        self.agent_id = agent_state.id
        await run_store.add_event(
            RunEvent(
                run_id=self.run_id,
                type=EventType.AGENT_SPAWNED,
                agent_id=self.agent_id,
                payload={"name": self.name, "role": self.role.value, "brief": brief},
            )
        )

    async def emit_event(self, event_type: EventType, payload: Optional[dict] = None) -> None:
        await run_store.add_event(
            RunEvent(
                run_id=self.run_id,
                type=event_type,
                agent_id=self.agent_id,
                timestamp=datetime.utcnow(),
                payload=payload or {},
            )
        )

    async def mark_status(self, status: AgentStatus, error: Optional[str] = None) -> None:
        if not self.agent_id:
            return
        await run_store.update_agent_status(self.run_id, self.agent_id, status=status, error=error)

    async def record_finding(self, content: str) -> None:
        if not self.agent_id:
            return
        await run_store.append_finding(self.run_id, self.agent_id, content)
        await self.emit_event(EventType.FINDING_RECORDED, {"content": content})

    async def plan_with_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return await self.llm.complete(prompt=prompt, system_prompt=system_prompt)

    @abc.abstractmethod
    async def run(self) -> Any:  # pragma: no cover - implemented by subclasses
        raise NotImplementedError
