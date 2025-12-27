# Multi-Agent Research Demo Architecture

## Objectives
- Recreate the orchestrator-worker multi-agent research workflow described in *How we built our multi-agent research system* while keeping fidelity to the lead researcher, specialized subagents, shared memory, and citation pass @How we built our multi-agent research system.md#29-107.
- Provide a functional, locally runnable demo that showcases agent creation, task assignment, iterative research, and result aggregation with a UI that visualizes agent interactions.
- Integrate with real LLMs via the `.env` configuration (OpenAI-compatible API hosted at `OPENAI_BASE_URL`) and include robust error handling for latency, rate limits, and tool failures.

## High-Level System Overview
```
┌──────────────┐        ┌────────────────┐        ┌─────────────────┐
│  Web Client  │ <────> │ FastAPI Backend│ <────> │ LLM + Tool APIs │
└──────────────┘  WS/HTTP└────────────────┘  HTTP └─────────────────┘
        │                         │                          │
        ▼                         ▼                          ▼
 Task creation UI      LeadResearcher Orchestrator   External knowledge
 (query + goals)        (agent graph manager)        + LLM generations
        │                         │
        ▼                         ▼
 Progress visualizer   Subagent pool (parallel async workers)
 (timelines, logs)        │            │
                          ▼            ▼
                Memory + Artifact store ──► CitationAgent synthesizer
```

### Backend Components
1. **FastAPI Application**
   - REST endpoints for launching research runs, fetching run status, downloading artifacts.
   - WebSocket channel for streaming agent events to the UI (state changes, tool calls, findings).
   - Dependency injection layer loads `.env` configuration and provides shared services.

2. **LLM Client Service**
   - Thin wrapper around OpenAI-compatible APIs configured via environment variables.
   - Supports retry/backoff, request tracing, and temperature overrides per agent type.

3. **Agent Framework**
   - `BaseAgent`: manages prompts, state, scratchpad, tool registry, and structured outputs.
   - `LeadResearcherAgent`: interprets user query, plans approach, spawns subagents, evaluates when to continue or finalize.
   - `ResearchSubagent`: executes delegated tasks (broad search, deep dive, synthesis) and emits findings + citations.
   - `CitationAgent`: post-processes aggregated findings and attaches citation metadata before final response (mirrors article pipeline @How we built our multi-agent research system.md#39-41).

4. **Task + Memory Layer**
   - In-memory store (later pluggable) tracking task graph, subagent assignments, and knowledge snippets.
   - Temporal log for UI playback and debugging (aligns with observability emphasis @How we built our multi-agent research system.md#41-82).

5. **Tooling Interfaces**
   - `SearchTool`: placeholder integration (can hit web search API or sample corpus).
   - `WorkspaceTool`: demonstrates querying structured data (e.g., stubbed Google Workspace docs) to reflect heterogeneous tool usage.
   - Tools implement a common contract so agents can inspect capabilities before invoking, reflecting tool selection heuristics @How we built our multi-agent research system.md#51-55.

6. **Simulation/Replay Mode**
   - Deterministic sandbox for demos when external network access is restricted. Uses seeded datasets but still routes prompts through the live LLM for reasoning and synthesis to fulfill "authentic" demonstrations.

### Frontend Components
1. **Vite + React Application**
   - Query builder form with presets for sample research tasks.
   - Live research console showing:
     - Agent graph (LeadResearcher + dynamic subagents) with status badges.
     - Timeline/log stream of events (tool calls, findings, decisions).
     - Token + tool usage counters (addresses scaling insights @How we built our multi-agent research system.md#23-60).
     - Final report viewer with citation references.

2. **State Management**
   - WebSocket client to subscribe to backend event stream.
   - React Query (or SWR) to poll REST endpoints for completed artifacts.

3. **Visualization**
   - D3 (or lightweight library) to animate agent creation & task assignments, emphasizing orchestrator-worker pattern.

### Data Flow
1. User submits research query via UI.
2. Backend instantiates a `ResearchRun` record, initializes LeadResearcherAgent with query + heuristics (effort scaling rules @How we built our multi-agent research system.md#45-61).
3. Lead agent plans tasks, logs plan to memory, and spawns subagents with explicit briefs (objectives, tools, expected outputs).
4. Subagents iterate autonomously: run tool calls, call LLM for reasoning, push findings and logs to EventBus.
5. Lead agent consumes findings, decides to continue or finalize. Once satisfied, aggregates knowledge graph and passes to the CitationAgent.
6. CitationAgent produces final structured report + citations, stored as artifact and pushed to UI.

### Error Handling & Reliability
- Retry logic with backoff for LLM/tool calls; circuit breaker for failing tools (mirrors production mitigations @How we built our multi-agent research system.md#75-85).
- Checkpointing of agent state per run to allow resume after transient failures.
- Structured tracing IDs propagate through events for debugging.

### Configuration & Secrets
- `.env` drives LLM connectivity and logging level.
- Pydantic settings module provides validated config; raise descriptive errors if keys missing.

### Implementation Plan Snapshot
1. **Backend foundation**: FastAPI project scaffolding, config, service container, stub endpoints.
2. **Agent framework**: base abstractions + in-memory stores, hooking into LLM client.
3. **Tool implementations**: initial search/workspace simulators with pluggable interface.
4. **End-to-end orchestration**: run lifecycle, event streaming, citation pass.
5. **Frontend**: Vite React app with WebSocket stream + visualization components.
6. **Docs & scripts**: setup instructions, sample datasets, run scripts.

This architecture document will be refined as implementation progresses; major deltas will be tracked in `docs/CHANGELOG.md`.
