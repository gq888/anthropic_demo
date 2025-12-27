"""Domain dataclasses representing research runs and agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .enums import AgentRole, AgentStatus, RunStatus


@dataclass(slots=True)
class AgentState:
    """Tracks the lifecycle of a single agent involved in a run."""

    id: str
    name: str
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    brief: Optional[str] = None
    findings: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass(slots=True)
class EvaluationResult:
    """Represents an LLM-judged evaluation of a research run output."""

    rubric_scores: Dict[str, float]
    overall_score: float
    passed: bool
    feedback: Optional[str] = None
    raw_judgement: Optional[str] = None


@dataclass(slots=True)
class ResearchRun:
    """Represents an orchestrated research workflow execution."""

    id: str
    query: str
    goal: Optional[str]
    status: RunStatus = RunStatus.CREATED
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    agents: Dict[str, AgentState] = field(default_factory=dict)
    plan: Optional[str] = None
    final_report: Optional[str] = None
    citations: List[dict] = field(default_factory=list)
    evaluation: Optional[EvaluationResult] = None

    def update_timestamp(self) -> None:
        self.updated_at = datetime.utcnow()
