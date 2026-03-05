"""FastAPI application for the Deployment Agent."""

from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.database import (
    init_db, create_project, list_projects, get_project, update_project_stage,
    delete_project, add_call_log, get_call_logs, get_plan, save_plan, STAGES,
)
from backend.orchestrator import run_all_agents, update_plan

app = FastAPI(title="Deployment Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_CALL_NOTES = """Met with VP of Digital Transformation (Klaus Weber) and Head of Contact Centre Operations (Sarah Mueller). Deutsche Telekom handles ~2.4M inbound support calls/month, currently using legacy IVR system built on Nuance. Core pain: 67% of calls still reach human agents despite IVR, average handle time is 8.4 minutes, CSAT sitting at 6.2/10. They're actively evaluating Conversational AI for Tier 1 support deflection - billing enquiries and account management are the highest volume, lowest complexity calls. Sarah (Head of Contact Centre) is clearly the champion - she brought this to the VP. Technical lead on their side asked specifically about GDPR compliance and whether voice data would leave EU servers. VP mentioned the CTO office needs to sign off on any infrastructure change. Current telephony stack is Genesys Cloud. They want to understand integration complexity before committing to a technical deep-dive. Asked us to come back with a proposed pilot structure. Next step: prepare pilot proposal and schedule technical session with their engineering team."""


async def _seed_demo():
    """Create Deutsche Telekom demo project with pre-populated call log and plan."""
    projects = list_projects()
    if any(p["client_name"] == "Deutsche Telekom" for p in projects):
        return

    project = create_project("Deutsche Telekom", "Telecommunications", "Discovery")
    add_call_log(project["id"], "2026-02-15", DEMO_CALL_NOTES)
    try:
        await update_plan(project["id"])
    except Exception:
        pass


@app.on_event("startup")
async def on_startup():
    init_db()
    await _seed_demo()


class BriefRequest(BaseModel):
    company_name: str
    role: str


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


EMPTY_PLAN = {
    "integration_map": "", "stakeholder_tracker": "", "open_questions": "",
    "risk_flags": "", "next_meeting_agenda": "", "technical_email": "",
    "executive_email": "",
}


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/stages")
async def get_stages():
    return STAGES


@app.post("/brief")
async def generate_brief(request: BriefRequest):
    brief = await run_all_agents(request.company_name, request.role)
    return {"brief": brief}


@app.post("/projects")
async def create_new_project(request: ProjectRequest):
    project = create_project(request.client_name, request.industry, request.stage)
    return project


@app.post("/projects/from-brief")
async def create_project_from_brief(request: SaveBriefRequest):
    project = create_project(request.company_name, request.role, "Prospect")
    brief_as_context = "**Initial Research Brief**\n\n" + request.brief
    save_plan(
        project_id=project["id"],
        integration_map=brief_as_context,
        stakeholder_tracker="",
        open_questions="",
        risk_flags="",
        next_meeting_agenda="",
        technical_email="",
        executive_email="",
    )
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
