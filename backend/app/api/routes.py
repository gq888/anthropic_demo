"""API routes for managing research runs."""

from __future__ import annotations

from typing import List, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.agents.lead_researcher import LeadResearcherAgent
from app.core.settings import Settings, get_settings
from app.models.enums import EventType, RunStatus
from app.models.events import RunEvent
from app.models.run import ResearchRun
from app.services.event_bus import event_bus
from app.services.run_store import run_store

router = APIRouter(prefix="/api", tags=["research"])


class CitationResponse(BaseModel):
    """Citation data structure for API responses."""
    citation: str
    url: Optional[str] = None


class RunSummaryResponse(BaseModel):
    """Enhanced run summary response with proper citation formatting."""
    id: str
    query: str
    goal: Optional[str] = None
    status: str
    plan: Optional[str] = None
    final_report: Optional[str] = None
    citations: List[CitationResponse] = []
    evaluation: Optional[dict] = None


BEIJING_TZ = ZoneInfo("Asia/Shanghai")


def format_beijing(timestamp):
    if timestamp is None:
        return None
    try:
        return timestamp.astimezone(BEIJING_TZ).isoformat()
    except AttributeError:
        return str(timestamp)


@router.post("/runs", response_model=dict)
async def create_run(
    payload: dict,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),
) -> dict:
    query = payload.get("query")
    goal = payload.get("goal")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    run = await run_store.create_run(query=query, goal=goal)

    async def orchestrate() -> None:
        try:
            agent = LeadResearcherAgent(run_id=run.id, query=query, goal=goal)
            await agent.run()
        except Exception as exc:  # noqa: BLE001 - handled by agent but guard background task
            await run_store.update_run_status(run.id, RunStatus.FAILED)
            await run_store.add_event(
                RunEvent(
                    run_id=run.id,
                    type=EventType.RUN_FAILED,
                    payload={"error": str(exc)},
                )
            )
            # raise exc

    background_tasks.add_task(orchestrate)
    return {"run_id": run.id, "status": run.status}


@router.get("/runs/{run_id}", response_model=RunSummaryResponse)
async def get_run(run_id: str) -> RunSummaryResponse:
    run = await run_store.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Format citations properly for frontend
    formatted_citations = []
    for citation in run.citations:
        if isinstance(citation, dict):
            formatted_citations.append(CitationResponse(
                citation=citation.get("citation", ""),
                url=citation.get("url")
            ))

    evaluation_payload = None
    if run.evaluation:
        evaluation_payload = {
            "rubric_scores": run.evaluation.rubric_scores,
            "overall_score": run.evaluation.overall_score,
            "passed": run.evaluation.passed,
            "feedback": run.evaluation.feedback,
        }

    return RunSummaryResponse(
        id=run.id,
        query=run.query,
        goal=run.goal,
        status=run.status.value,
        plan=run.plan,
        final_report=run.final_report,
        citations=formatted_citations,
        evaluation=evaluation_payload,
    )


@router.get("/runs/{run_id}/events", response_model=List[dict])
async def get_run_events(run_id: str) -> List[dict]:
    events = await run_store.get_events(run_id)
    return [
        {
            "type": event.type.value,
            "timestamp": format_beijing(event.timestamp),
            "payload": event.payload,
            "agent_id": event.agent_id,
        }
        for event in events
    ]


@router.websocket("/ws/runs/{run_id}")
async def run_events_ws(websocket: WebSocket, run_id: str) -> None:
    run = await run_store.get_run(run_id)
    if not run:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    queue = await event_bus.subscribe(run_id)
    try:
        await websocket.send_json({"type": "run_state", "status": run.status.value})
        # Send replay of existing events for late subscribers
        history = await run_store.get_events(run_id)
        for event in history:
            await websocket.send_json(
                {
                    "type": event.type.value,
                    "timestamp": format_beijing(event.timestamp),
                    "payload": event.payload,
                    "agent_id": event.agent_id,
                }
            )

        while True:
            event = await queue.get()
            
            # Handle special formatting for citation events
            if event.type.value == "citations_generated":
                payload = event.payload.copy()
                # Ensure citations are properly formatted
                if "citations" in payload:
                    formatted_citations = []
                    for citation in payload["citations"]:
                        if isinstance(citation, dict):
                            formatted_citations.append({
                                "citation": citation.get("citation", ""),
                                "url": citation.get("url", "")
                            })
                    payload["citations"] = formatted_citations
                
                await websocket.send_json(
                    {
                        "type": event.type.value,
                        "timestamp": format_beijing(event.timestamp),
                        "payload": payload,
                        "agent_id": event.agent_id,
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": event.type.value,
                        "timestamp": format_beijing(event.timestamp),
                        "payload": event.payload,
                        "agent_id": event.agent_id,
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.unsubscribe(run_id, queue)
