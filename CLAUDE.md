# Deployment Agent — ElevenLabs FDE Workspace

Two-console workspace for an ElevenLabs Forward Deployed Engineer Strategist. Generates prospect research briefs and manages active client projects with AI-synthesized plans.

## Architecture

- **Backend**: Python + FastAPI (`backend/api.py`)
- **Frontend**: Single-page vanilla HTML/CSS/JS (`frontend/index.html`)
- **Database**: SQLite (`data/deployment_agent.db`) — projects, call_logs, plans tables
- **AI**: Anthropic API (Claude) for LLM calls
- **Search**: Tavily API for web research
- **Config**: `configs/elevenlabs.json` — product context, deal stages, question banks

## Project Structure

```
backend/
  api.py              — FastAPI app, all endpoints
  orchestrator.py     — Parallel agent runner, synthesis, plan updates
  database.py         — SQLite layer (projects, call_logs, plans)
  agents/
    company_intel.py  — Company background research
    use_case.py       — Deployment use case identification
    stakeholder.py    — Decision-maker mapping
    objection.py      — Objection anticipation
    playbook.py       — 30/60/90 day roadmap
configs/
  elevenlabs.json     — Product context injected into all agent prompts
frontend/
  index.html          — Two-panel workspace UI
```

## Key Flows

1. **Prospect Research**: Input (company + role) -> 5 parallel agents -> Synthesis -> One-page brief
2. **Project Management**: Create project -> Log calls -> Auto-synthesize plan (integration map, stakeholder tracker, next meeting prep)

## API Endpoints

- `GET /health`
- `POST /brief` — `{company_name, role}` -> research brief
- `POST /projects` — `{client_name, industry, stage?}`
- `GET /projects` — list all
- `POST /projects/{id}/log` — `{date, notes}` -> auto-triggers plan update
- `GET /projects/{id}/plan` — latest synthesized plan

## API Keys

Required environment variables (see `.env.example`):
- `ANTHROPIC_API_KEY`
- `TAVILY_API_KEY`

## Commands

```bash
pip install -r requirements.txt
uvicorn backend.api:app --reload
```

## Conventions

- Use the Anthropic Python SDK (`anthropic` package) for all Claude API calls
- Use `claude-sonnet-4-6` model for all agent and synthesis calls
- All agents accept `product_context` param — loaded from config and injected by orchestrator
- Use async/await for parallel agent execution (`asyncio.gather`)
- Tavily searches wrapped in `run_in_executor` (sync client)
- Type hints on all function signatures
