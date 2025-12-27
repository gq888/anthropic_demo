# Multi-Agent Research Demo

A full-stack demonstration inspired by Anthropic's article **“How we built our multi-agent research system.”** The goal is to reproduce the orchestrator-worker architecture where a lead researcher agent plans the investigation, spawns specialized subagents, and hands results to a citation agent for final synthesis. The demo runs locally with your `.env` LLM credentials and showcases the live workflow via a React dashboard.

## Repository layout

```
backend/
  app/
    agents/            # LeadResearcher, Subagents, Citation agent
    api/               # FastAPI REST + WebSocket routes
    core/              # Settings and config loading
    llm/               # OpenAI-compatible HTTP client wrapper
    models/            # Run/Agent state dataclasses and enums
    services/          # RunStore, EventBus, tool abstractions
    tools/             # Synthetic Search tool for offline demos
  pyproject.toml
frontend/
  src/                 # React + Vite dashboard (events, plan, report)
docs/
  ARCHITECTURE.md      # Detailed architecture & implementation plan
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- `.env` file at repo root with OpenAI-compatible settings (sample already provided).

Example `.env` (already included):
```
OPENAI_API_KEY=...
OPENAI_MODEL=Qwen/Qwen3-8B
OPENAI_BASE_URL=https://api.siliconflow.cn/v1
OPENAI_TEMPERATURE=0.7
MAX_TOKENS=1024
LOG_LEVEL=INFO
```

## Backend setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate  # or use uv/poetry if preferred
pip install -e .
uvicorn app.main:app --reload --port 8000
```

This starts the FastAPI server with:
- `POST /api/runs` to launch a research run (background LeadResearcher agent)
- `GET /api/runs/{run_id}` to inspect run state and final report
- `GET /api/runs/{run_id}/events` for historical events
- `WS /api/ws/runs/{run_id}` streaming live RunEvents via the in-memory EventBus

## Frontend setup

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

Environment variables (optional) can override API endpoints by creating a `.env` in `frontend/` with Vite-prefixed keys:
```
VITE_API_BASE=http://localhost:8000/api
VITE_WS_BASE=ws://localhost:8000/api/ws
```

## Running the demo

1. Start the backend server (`uvicorn app.main:app --reload`).
2. Launch the frontend dev server (`npm run dev`).
3. Open `http://localhost:5173` and submit a research query + goal.
4. Observe the **Live Event Stream** updating in real time (plan creation, subagent findings, citation pass).
5. After completion, inspect the **Run Summary** section for the synthesized report and citations.

The subagents currently use a deterministic `SearchTool` seeded with representative documents so the flow works without real web access. LLM calls still go to the configured base URL for reasoning/stitching steps.

## Testing & future extensions

- The architecture includes clear seams (LLM client, tools, RunStore) to plug in real web search or workspace tools.
- Add automated tests with `pytest` by mocking the LLM client (fixtures pending).
- Extend the frontend with richer agent graphs or token/tool usage metrics referenced in the article.
- Deploy via Docker by wrapping `uvicorn` and `vite build` outputs once ready.

## Troubleshooting

- **TypeScript errors in the frontend**: run `npm install` to pull React/React Query types; restart `npm run dev`.
- **LLM errors (502/504)**: check `.env` credentials and ensure the proxy endpoint (e.g., SiliconFlow) is reachable.
- **WebSocket not connecting**: confirm backend server is reachable on `localhost:8000` and no firewall blocks `ws://` requests.

This README, together with `docs/ARCHITECTURE.md`, should provide everything needed to run and extend the multi-agent research demo.
