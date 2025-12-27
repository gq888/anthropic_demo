"""Enumerations shared across the backend."""

from __future__ import annotations

from enum import Enum


class AgentRole(str, Enum):
    LEAD_RESEARCHER = "lead_researcher"
    SUBAGENT = "subagent"
    CITATION = "citation"


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class EventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    AGENT_SPAWNED = "agent_spawned"
    AGENT_COMPLETED = "agent_completed"
    AGENT_FAILED = "agent_failed"
    TOOL_CALL = "tool_call"
    FINDING_RECORDED = "finding_recorded"
    PLAN_UPDATED = "plan_updated"
    CITATIONS_GENERATED = "citations_generated"
