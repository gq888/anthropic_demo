"""Lead researcher agent orchestrating the research workflow."""

from __future__ import annotations

from typing import Optional

from app.agents.base import BaseAgent
from app.agents.citation import CitationAgent
from app.agents.subagent import ResearchSubagent
from app.models.enums import AgentRole, AgentStatus, EventType, RunStatus
from app.utils.json_parser import extract_json
from app.services.run_store import run_store


class LeadResearcherAgent(BaseAgent):
    """Lead agent that plans the research and manages subagents."""

    def __init__(self, run_id: str, query: str, goal: Optional[str] = None) -> None:
        super().__init__(run_id, name="Lead Researcher", role=AgentRole.LEAD_RESEARCHER)
        self.query = query
        self.goal = goal

    async def run(self) -> None:
        await self.register(brief=f"Investigate: {self.query}")
        await self.mark_status(AgentStatus.RUNNING)
        await run_store.update_run_status(self.run_id, RunStatus.RUNNING)
        await self.emit_event(EventType.RUN_STARTED, {"query": self.query, "goal": self.goal})

        plan_prompt = (
            "You orchestrate multiple research subagents. Produce a structured plan "
            "with bullet points describing distinct investigative tracks and suggest up to three subagent tasks."
        )
        plan = await self.plan_with_llm(
            prompt=f"Query: {self.query}\nGoal: {self.goal or 'Provide best answer'}",
            system_prompt=plan_prompt,
        )
        await run_store.save_plan(self.run_id, plan)
        await self.emit_event(EventType.PLAN_UPDATED, {"plan": plan})

        tasks = [segment.strip("- ").strip() for segment in plan.splitlines() if segment.strip().startswith("-")]
        if not tasks:
            tasks = [self.query]

        subagents = [ResearchSubagent(self.run_id, task, self.query) for task in tasks[:3]]
        subagent_outputs = []
        for agent in subagents:
            result = await agent.run()
            subagent_outputs.append(result)

        summary_prompt = "Summarize key findings from the research plan, highlighting distinct angles and open questions."
        summary = await self.plan_with_llm(
            prompt="\n".join(agent_task for agent_task in tasks),
            system_prompt=summary_prompt,
        )

        # Prepare enhanced findings with better source information for citation agent
        enhanced_findings = []
        for output in subagent_outputs:
            if isinstance(output, dict):
                enhanced_findings.append({
                    "summary": output.get("summary", ""),
                    "sources": output.get("sources", [])
                })
        
        citation_agent = CitationAgent(self.run_id, enhanced_findings)
        citations_response = await citation_agent.run()
        
        # Ensure proper JSON extraction and validation
        if isinstance(citations_response, dict):
            citation_payload = citations_response
        else:
            citation_payload = extract_json(citations_response) if isinstance(citations_response, str) else {"report": "", "citations": []}

        # Extract and validate citation data
        final_report = citation_payload.get("report", summary)
        final_citations = citation_payload.get("citations", [])
        
        # Ensure citations are in the correct format
        formatted_citations = []
        for citation in final_citations:
            if isinstance(citation, dict):
                formatted_citations.append({
                    "citation": citation.get("citation", ""),
                    "url": citation.get("url", "")
                })
        
        await run_store.save_final_report(
            self.run_id,
            report=final_report,
            citations=formatted_citations,
        )
        
        # Emit event for final report completion
        await self.emit_event(EventType.RUN_COMPLETED, {
            "summary": summary,
            "citation_count": len(formatted_citations),
            "report_length": len(final_report)
        })
        await run_store.update_run_status(self.run_id, RunStatus.COMPLETED)
        await self.mark_status(AgentStatus.COMPLETED)
        await self.emit_event(EventType.RUN_COMPLETED, {"summary": summary})
