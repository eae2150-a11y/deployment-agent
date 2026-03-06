"""FastAPI application for the Deployment Agent."""

import json
import logging
from typing import Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    init_db, create_project, list_projects, get_project, update_project_stage,
    update_project_brief_data,
    delete_project, add_call_log, get_call_logs, get_plan, save_plan, STAGES,
)
from backend.orchestrator import run_all_agents, update_plan
from backend.llm import chat
from backend.seed_data import seed_gorillas, GORILLAS_NEXT_ACTION

log = logging.getLogger(__name__)

app = FastAPI(title="Deployment Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    init_db()
    seed_gorillas()


@app.get("/seed-next-actions")
async def get_seed_next_actions():
    """Return pre-populated next-action text for seeded projects."""
    projects = list_projects()
    actions = {}
    for p in projects:
        if p["client_name"] == "Gorillas":
            actions[str(p["id"])] = GORILLAS_NEXT_ACTION
    return actions


class BriefRequest(BaseModel):
    company_name: str
    role: str = "Deployment Strategist"
    notes: Optional[str] = ""


class ProjectRequest(BaseModel):
    client_name: str
    industry: str
    stage: str = "Prospect"


class CallLogRequest(BaseModel):
    date: str
    notes: str


class StageRequest(BaseModel):
    stage: str


class SaveBriefRequest(BaseModel):
    company_name: str
    role: str
    brief: str
    industry: str = ""
    product_match: Optional[dict] = None
    signals: Optional[dict] = None
    job_signals: Optional[dict] = None
    funding_signals: Optional[dict] = None


IMPL_PLAN_PROMPT = """You are an ElevenLabs FDE creating a concrete implementation plan for a prospect.

Company: {company_name} | Industry: {industry}
Primary Product: {primary_product}
Recommended Architecture: {recommended_architecture}
Integration Pattern: {integration_pattern}
Recommended Model: {recommended_model}
Migration Complexity: {migration_complexity}
Existing Voice Stack: {existing_voice_stack}
Is API-First: {is_api_first} | Needs Realtime: {needs_realtime}

Write three phases. Be specific to THIS company. Keep each phase to 3-5 bullet points. Be concise.

Phase 1 — POC (week 1-2): what to build, which EL API, success criteria
Phase 2 — Integration (week 3-6): stack fit, auth pattern, model choice, edge cases
Phase 3 — Scale (week 6+): monitoring, voice consistency, product expansion

Return ONLY valid JSON (keep each phase under 500 chars):
{{
  "phase_1": "bullet points as a single string",
  "phase_2": "bullet points as a single string",
  "phase_3": "bullet points as a single string"
}}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


EMPTY_PLAN = {
    "integration_map": "", "stakeholder_tracker": "", "open_questions": "",
    "risk_flags": "", "next_meeting_agenda": "", "technical_email": "",
    "executive_email": "",
}


@app.get("/")
async def root():
    return FileResponse("frontend/index.html")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stages")
async def get_stages():
    return STAGES


@app.post("/brief")
async def generate_brief(request: BriefRequest):
    result = await run_all_agents(request.company_name, request.role, request.notes or "")
    return {
        "brief": result["brief"],
        "signals": result["signals"],
        "product_match": result["product_match"],
        "job_signals": result["job_signals"],
        "funding_signals": result["funding_signals"],
    }


@app.post("/projects")
async def create_new_project(request: ProjectRequest):
    project = create_project(request.client_name, request.industry, request.stage)
    return project


@app.post("/projects/from-brief")
async def create_project_from_brief(request: SaveBriefRequest):
    industry = request.industry or request.role
    pm = request.product_match or {}
    signals = request.signals or {}

    # Generate implementation plan using Claude
    implementation_plan = {"phase_1": "", "phase_2": "", "phase_3": ""}
    if pm.get("primary_product"):
        try:
            prompt = IMPL_PLAN_PROMPT.format(
                company_name=request.company_name,
                industry=industry,
                primary_product=pm.get("primary_product", "Unknown"),
                recommended_architecture=pm.get("recommended_architecture", "REST batch"),
                integration_pattern=pm.get("integration_pattern", ""),
                recommended_model=pm.get("recommended_model", "Eleven Multilingual v2"),
                migration_complexity=pm.get("migration_complexity", "medium"),
                existing_voice_stack=", ".join(signals.get("existing_voice_stack", [])) or "None detected",
                is_api_first=signals.get("is_api_first", False),
                needs_realtime=signals.get("needs_realtime", False),
            )
            text = await chat(
                prompt=prompt, max_tokens=2048,
                system="Return only valid JSON, no markdown. Keep each phase concise.",
            )
            implementation_plan = json.loads(_strip_fences(text))
        except Exception as e:
            log.error("Implementation plan generation failed: %s", e, exc_info=True)

    brief_data = json.dumps({
        "company": request.company_name,
        "brief": request.brief,
        "product_match": pm,
        "signals": signals,
        "job_signals": request.job_signals or {},
        "funding_signals": request.funding_signals or {},
        "implementation_plan": implementation_plan,
    })

    project = create_project(request.company_name, industry, "Prospect", brief_data=brief_data)
    return project


@app.get("/projects")
async def get_all_projects():
    return list_projects()


@app.get("/projects/{project_id}")
async def get_single_project(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.patch("/projects/{project_id}/stage")
async def change_project_stage(project_id: int, request: StageRequest):
    if request.stage not in STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Must be one of: {STAGES}")
    project = update_project_stage(project_id, request.stage)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.delete("/projects/{project_id}")
async def remove_project(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    delete_project(project_id)
    return {"ok": True}


@app.post("/projects/{project_id}/log")
async def add_project_log(project_id: int, request: CallLogRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    log = add_call_log(project_id, request.date, request.notes)
    try:
        await update_plan(project_id)
    except ValueError:
        pass
    return log


@app.get("/projects/{project_id}/logs")
async def get_project_logs(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return get_call_logs(project_id)


@app.get("/projects/{project_id}/plan")
async def get_project_plan(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    plan = get_plan(project_id)
    if not plan:
        return dict(project_id=project_id, **EMPTY_PLAN)
    return plan
