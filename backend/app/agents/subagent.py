"""Research subagent implementation."""

from __future__ import annotations

from typing import Any

from app.agents.base import BaseAgent
from app.models.enums import AgentRole, AgentStatus, EventType
from app.tools.search import SearchTool


class ResearchSubagent(BaseAgent):
    """Executes a delegated research task and reports findings."""

    def __init__(self, run_id: str, task: str, query: str) -> None:
        super().__init__(run_id, name=f"Subagent: {task[:24]}", role=AgentRole.SUBAGENT)
        self.task = task
        self.query = query
        self.search = SearchTool()

    async def run(self) -> Any:
        await self.register(brief=self.task)
        await self.mark_status(AgentStatus.RUNNING)
        search_results = await self.search.search(self.task)
        research_prompt = (
            "You are a specialized research subagent."
            "\nTask: {task}\nOverall query: {query}\n"
            "Evidence:\n{evidence}\n"
            "Synthesize a concise bullet summary referencing top sources."
        ).format(
            task=self.task,
            query=self.query,
            evidence="\n".join(f"- {res.title}: {res.snippet}" for res in search_results),
        )
        result = await self.plan_with_llm(research_prompt)
        await self.record_finding(result)
        await self.emit_event(
            EventType.AGENT_COMPLETED,
            {"result": result, "sources": [res.url for res in search_results]},
        )
        await self.mark_status(AgentStatus.COMPLETED)
        return {"summary": result, "sources": [res.url for res in search_results]}
