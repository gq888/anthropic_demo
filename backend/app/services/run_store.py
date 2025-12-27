"""In-memory storage for research runs and their agent state."""

from __future__ import annotations

import asyncio
from typing import Dict, Iterable, Optional
from uuid import uuid4

from app.models.enums import AgentRole, AgentStatus, RunStatus
from app.models.events import RunEvent
from app.services.event_bus import event_bus
from app.models.run import AgentState, ResearchRun, EvaluationResult


class RunStore:
    """Manages lifecycle of ResearchRun objects and their events."""

    def __init__(self) -> None:
        self._runs: Dict[str, ResearchRun] = {}
        self._events: Dict[str, list[RunEvent]] = {}
        self._lock = asyncio.Lock()

    async def create_run(self, query: str, goal: Optional[str] = None) -> ResearchRun:
        async with self._lock:
            run_id = uuid4().hex
            run = ResearchRun(id=run_id, query=query, goal=goal)
            self._runs[run_id] = run
            self._events[run_id] = []
            return run

    async def get_run(self, run_id: str) -> Optional[ResearchRun]:
        async with self._lock:
            return self._runs.get(run_id)

    async def list_runs(self) -> Iterable[ResearchRun]:
        async with self._lock:
            return list(self._runs.values())

    async def add_event(self, event: RunEvent) -> None:
        async with self._lock:
            if event.run_id not in self._events:
                self._events[event.run_id] = []
            buffer = self._events[event.run_id]
            buffer.append(event)
        await event_bus.publish(event)

    async def get_events(self, run_id: str) -> list[RunEvent]:
        async with self._lock:
            return list(self._events.get(run_id, []))

    async def add_agent(
        self,
        run_id: str,
        name: str,
        role: AgentRole,
        brief: Optional[str] = None,
    ) -> AgentState:
        async with self._lock:
            run = self._runs[run_id]
            agent_id = uuid4().hex
            agent = AgentState(id=agent_id, name=name, role=role, brief=brief)
            run.agents[agent_id] = agent
            run.update_timestamp()
            return agent

    async def update_agent_status(
        self,
        run_id: str,
        agent_id: str,
        status: AgentStatus,
        error: Optional[str] = None,
    ) -> None:
        async with self._lock:
            agent = self._runs[run_id].agents[agent_id]
            agent.status = status
            agent.error = error
            run = self._runs[run_id]
            run.update_timestamp()

    async def append_finding(
        self,
        run_id: str,
        agent_id: str,
        finding: str,
    ) -> None:
        async with self._lock:
            agent = self._runs[run_id].agents[agent_id]
            agent.findings.append(finding)
            agent.status = AgentStatus.RUNNING
            run = self._runs[run_id]
            run.update_timestamp()

    async def update_run_status(self, run_id: str, status: RunStatus) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.status = status
            run.update_timestamp()

    async def save_plan(self, run_id: str, plan: str) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.plan = plan
            run.update_timestamp()

    async def save_final_report(
        self,
        run_id: str,
        report: str,
        citations: Optional[list[dict]] = None,
    ) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.final_report = report
            run.citations = citations or []
            run.update_timestamp()

    async def save_evaluation(self, run_id: str, evaluation: EvaluationResult) -> None:
        async with self._lock:
            run = self._runs[run_id]
            run.evaluation = evaluation
            run.update_timestamp()


run_store = RunStore()
