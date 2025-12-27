"""Citation agent that synthesizes final report with references."""

from __future__ import annotations

import json
import re
from typing import Any, List, Sequence

from app.agents.base import BaseAgent
from app.models.enums import AgentRole, AgentStatus, EventType


class CitationAgent(BaseAgent):
    """Processes findings and attaches source attributions."""

    def __init__(self, run_id: str, findings: Sequence[dict]) -> None:
        super().__init__(run_id, name="Citation Agent", role=AgentRole.CITATION)
        self.findings = list(findings)

    def _extract_urls_from_sources(self, sources: List[str]) -> List[str]:
        """Extract URLs from source strings."""
        urls = []
        url_pattern = re.compile(r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+')
        for source in sources:
            found_urls = url_pattern.findall(source)
            urls.extend(found_urls)
        return urls

    def _format_citations(self, report: str, sources: List[List[str]]) -> tuple[str, List[dict]]:
        """Format citations and create citation entries."""
        citations = []
        formatted_report = report
        
        # Process each finding's sources
        citation_counter = 1
        for finding_sources in sources:
            urls = self._extract_urls_from_sources(finding_sources)
            for url in urls:
                # Create citation entry
                citation_text = f"[{citation_counter}]"
                citations.append({
                    "citation": f"Source {citation_counter}",
                    "url": url
                })
                
                # Add citation marker to report (if not already present)
                if citation_text not in formatted_report:
                    # Add citation at the end of relevant sentences or paragraphs
                    formatted_report += f" {citation_text}"
                
                citation_counter += 1
        
        return formatted_report, citations

    async def run(self) -> Any:
        await self.register(brief="Attach citations to synthesized report")
        await self.mark_status(AgentStatus.RUNNING)
        
        # Collect all findings and sources
        all_sources = []
        findings_text = []
        
        for idx, finding in enumerate(self.findings, start=1):
            summary = finding.get("summary", "")
            sources = finding.get("sources", [])
            all_sources.append(sources)
            
            if summary:
                findings_text.append(f"Finding {idx}: {summary}")
            
            if sources:
                findings_text.append(f"Sources: {', '.join(sources)}")

        # Create comprehensive prompt for citation generation
        prompt_lines = [
            "You are a research citation specialist. Your task is to:",
            "1. Synthesize the research findings into a coherent report",
            "2. Add proper citations with source URLs",
            "3. Format the output as JSON with 'report' and 'citations' keys",
            "",
            "Research Findings:",
            *findings_text,
            "",
            "Instructions:",
            "- Create a comprehensive research report based on the findings",
            "- Include inline citations like [1], [2], etc. in the report",
            "- List all sources with their URLs in the citations array",
            "- Make sure each citation has both 'citation' text and 'url' if available",
            "",
            "Output format:",
            '{"report": "Your synthesized report with [1], [2] citations...", "citations": [{"citation": "Source 1", "url": "https://example.com"}, ...]}'
        ]
        
        response = await self.plan_with_llm("\n".join(prompt_lines))
        
        # Parse the LLM response and ensure proper format
        try:
            # Try to extract JSON from the response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                citation_data = json.loads(json_match.group())
            else:
                # Fallback: create basic citation structure
                citation_data = {
                    "report": response,
                    "citations": []
                }
        except (json.JSONDecodeError, AttributeError):
            # If JSON parsing fails, create structured output manually
            formatted_report, citations = self._format_citations(response, all_sources)
            citation_data = {
                "report": formatted_report,
                "citations": citations
            }
        
        # Ensure citations array exists and has proper format
        if "citations" not in citation_data:
            citation_data["citations"] = []
        
        # Validate citation format
        valid_citations = []
        for citation in citation_data.get("citations", []):
            if isinstance(citation, dict) and "citation" in citation:
                valid_citations.append({
                    "citation": citation["citation"],
                    "url": citation.get("url", "")
                })
        
        citation_data["citations"] = valid_citations
        
        # Emit specific citation generation event
        await self.emit_event(EventType.CITATIONS_GENERATED, {
            "citations": valid_citations,
            "citation_count": len(valid_citations),
            "report_preview": citation_data.get("report", "")[:200] + "..." if len(citation_data.get("report", "")) > 200 else citation_data.get("report", "")
        })
        
        await self.emit_event(EventType.AGENT_COMPLETED, {
            "citation_response": citation_data,
            "report_length": len(citation_data.get("report", "")),
            "citation_count": len(valid_citations)
        })
        await self.mark_status(AgentStatus.COMPLETED)
        return citation_data
