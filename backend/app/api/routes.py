"""API routes for managing research runs."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.agents.lead_researcher import LeadResearcherAgent
from app.core.settings import Settings, get_settings
from app.models.enums import RunStatus
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
        agent = LeadResearcherAgent(run_id=run.id, query=query, goal=goal)
        await agent.run()

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
    
    return RunSummaryResponse(
        id=run.id,
        query=run.query,
        goal=run.goal,
        status=run.status.value,
        plan=run.plan,
        final_report=run.final_report,
        citations=formatted_citations
    )


@router.get("/runs/{run_id}/events", response_model=List[dict])
async def get_run_events(run_id: str) -> List[dict]:
    events = await run_store.get_events(run_id)
    return [
        {
            "type": event.type.value,
            "timestamp": event.timestamp,
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
                    "timestamp": event.timestamp.isoformat(),
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
                        "timestamp": event.timestamp.isoformat(),
                        "payload": payload,
                        "agent_id": event.agent_id,
                    }
                )
            else:
                await websocket.send_json(
                    {
                        "type": event.type.value,
                        "timestamp": event.timestamp.isoformat(),
                        "payload": event.payload,
                        "agent_id": event.agent_id,
                    }
                )
    except WebSocketDisconnect:
        pass
    finally:
        await event_bus.unsubscribe(run_id, queue)
