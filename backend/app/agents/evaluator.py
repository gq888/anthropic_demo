"""Evaluation agent that scores research outputs via LLM judge."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from app.agents.base import BaseAgent
from app.models.enums import AgentRole, AgentStatus, EventType

EVALUATION_PROMPT = """
You are an impartial evaluation judge for research reports.
Evaluate the provided research output using the rubric below. Respond ONLY with JSON using the schema:
{
  "rubric_scores": {
    "factual_accuracy": number between 0 and 1,
    "citation_accuracy": number between 0 and 1,
    "completeness": number between 0 and 1,
    "source_quality": number between 0 and 1,
    "tool_efficiency": number between 0 and 1
  },
  "overall_score": number between 0 and 1,
  "passed": boolean,
  "feedback": string,
  "raw_judgement": string optional analysis
}

Rubric definitions:
1. factual_accuracy – do claims align with evidence from provided citations?
2. citation_accuracy – do inline citations correctly reference the supporting sources?
3. completeness – does the report address the research query and goal thoroughly?
4. source_quality – are the sources credible, relevant, and preferentially primary?
5. tool_efficiency – were tools used effectively without unnecessary calls?

Mark "passed" true if overall_score >= 0.7. Keep answers concise.
"""


class EvaluationAgent(BaseAgent):
    """Uses the LLM judge prompt to evaluate final research output."""

    def __init__(self, run_id: str, report: str, citations: list[dict], plan: Optional[str] = None) -> None:
        super().__init__(run_id, name="Evaluation Agent", role=AgentRole.EVALUATOR)
        self.report = report
        self.citations = citations
        self.plan = plan

    @staticmethod
    def _default_payload(raw_response: str) -> Dict[str, Any]:
        return {
            "rubric_scores": {},
            "overall_score": 0.0,
            "passed": False,
            "feedback": "Evaluation model returned an unparseable response.",
            "raw_judgement": raw_response,
        }

    @staticmethod
    def _normalise_scores(scores: Dict[str, Any]) -> Dict[str, float]:
        normalised: Dict[str, float] = {}
        for key, value in scores.items():
            try:
                score = float(value)
            except (TypeError, ValueError):
                score = 0.0
            normalised[key] = max(0.0, min(1.0, score))
        return normalised

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        candidate: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, dict):
                candidate = parsed
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group())
                    if isinstance(parsed, dict):
                        candidate = parsed
                except json.JSONDecodeError:
                    candidate = None

        if candidate is None:
            return self._default_payload(raw_response)

        rubric_scores_raw = candidate.get("rubric_scores")
        rubric_scores = rubric_scores_raw if isinstance(rubric_scores_raw, dict) else {}
        normalised_scores = self._normalise_scores(rubric_scores)

        overall_score_raw = candidate.get("overall_score")
        try:
            overall_score = float(overall_score_raw)
        except (TypeError, ValueError):
            overall_score = sum(normalised_scores.values()) / len(normalised_scores) if normalised_scores else 0.0
        overall_score = max(0.0, min(1.0, overall_score))

        passed_raw = candidate.get("passed")
        if isinstance(passed_raw, bool):
            passed = passed_raw
        elif isinstance(passed_raw, (int, float)):
            passed = bool(passed_raw)
        else:
            passed = overall_score >= 0.7

        feedback_raw = candidate.get("feedback")
        feedback = str(feedback_raw) if feedback_raw is not None else None

        raw_judgement_raw = candidate.get("raw_judgement")
        raw_judgement = str(raw_judgement_raw) if raw_judgement_raw is not None else raw_response

        return {
            "rubric_scores": normalised_scores,
            "overall_score": overall_score,
            "passed": passed,
            "feedback": feedback,
            "raw_judgement": raw_judgement,
        }

    async def run(self) -> Dict[str, Any]:
        await self.register(brief="Score the final report using evaluation rubric")
        await self.mark_status(AgentStatus.RUNNING)

        evaluation_input = {
            "plan": self.plan,
            "report": self.report,
            "citations": self.citations,
        }
        prompt_payload = json.dumps(evaluation_input, ensure_ascii=False, indent=2)

        raw_response = await self.plan_with_llm(
            prompt=f"Research Output to evaluate:\n{prompt_payload}",
            system_prompt=EVALUATION_PROMPT,
        )

        await self.emit_event(
            EventType.TOOL_CALL,
            {"tool": "llm_judge", "input_bytes": len(prompt_payload.encode("utf-8"))},
        )

        parsed = self._parse_response(raw_response)

        await self.emit_event(
            EventType.EVALUATION_COMPLETED,
            {
                "overall_score": parsed["overall_score"],
                "passed": parsed["passed"],
                "rubric_scores": parsed["rubric_scores"],
                "feedback": parsed.get("feedback"),
            },
        )

        await self.mark_status(AgentStatus.COMPLETED)
        await self.emit_event(
            EventType.AGENT_COMPLETED,
            {"overall_score": parsed["overall_score"], "passed": parsed["passed"]},
        )

        parsed["raw_response"] = raw_response
        return parsed
