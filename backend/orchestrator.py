"""Orchestrator that runs research agents in parallel and synthesizes results."""

import asyncio
import json
import os

import anthropic
from dotenv import load_dotenv

from backend.agents.company_intel import research_company
from backend.agents.use_case import research_use_cases
from backend.agents.stakeholder import research_stakeholders
from backend.agents.objection import research_objections
from backend.agents.playbook import research_playbook
from backend.agents.critic import review_outputs
from backend.database import get_call_logs, get_project, save_plan

load_dotenv()

anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "elevenlabs.json")

def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


SYNTHESIS_PROMPT = """You are a deployment strategist preparing for your first call with a new enterprise prospect. You work as an ElevenLabs Forward Deployed Engineer.

Using the 5 research reports and the critic's quality review below, write a clean one-page brief with these sections:

1. **Company Overview**
2. **Top Use Cases**
3. **Key Stakeholders**
4. **Likely Objections**
5. **30/60/90 Day Playbook**
6. **Opening Pitch** (2-3 sentences the FDE could use to open the first call)
7. **Watch Out** (brief note on any low-confidence areas or gaps the FDE should be aware of, informed by the critic review)

Be concise and practical. This should fit on one page and be immediately useful for the call. Where the critic flagged contradictions or weak reasoning, resolve them in favor of the most well-supported evidence. Where critical gaps exist, acknowledge them rather than papering over them.

--- Company Intel ---
{company_intel}

--- Use Cases ---
{use_cases}

--- Stakeholders ---
{stakeholders}

--- Objections ---
{objections}

--- Playbook ---
{playbook}

--- Critic Review ---
{critic_review}"""


PLAN_PROMPT = """You are an ElevenLabs Forward Deployed Engineer managing an active client project.

Client: {client_name} ({industry})
Current stage: {stage}

Below are all the call logs from this engagement so far:

{call_logs}

Based on these call logs, produce exactly 7 sections using the exact headers below. Be specific and grounded in what was actually discussed. Don't invent details not in the logs.

## Integration Map
What systems need connecting? What's the technical architecture? List APIs, data flows, and dependencies discussed. If technical details haven't been discussed yet, note what needs to be discovered.

## Stakeholder Tracker
Who has been mentioned? For each person, note their name, title/role, whether they're a champion/neutral/blocker, and any key quotes or positions they've taken. Include sentiment signals.

## Open Questions
List all unanswered items from the calls that need resolving before the deal can move forward. Group by category (technical, commercial, legal, organizational) if applicable.

## Risk Flags
What could kill or delay this deal? For each risk, assign severity (High/Medium/Low) and suggest a mitigation approach. Be honest about red flags.

## Next Meeting Agenda
Suggest a structured agenda for the next call based on what's unresolved:
- 3-5 specific questions to ask
- Key talking points to advance the deal
- Any risks or blockers to address proactively

## Technical Follow-Up Email
Draft a professional email to the technical contact. Confirm what was discussed technically, list open technical questions, and propose next steps. Keep it concise and specific. Start with "Subject:" line.

## Executive Follow-Up Email
Draft a shorter email to the executive sponsor. Focus on business value, key outcomes discussed, and next steps. No technical details. Start with "Subject:" line."""


async def run_all_agents(company_name: str, role: str) -> str:
    """Fire all 5 research agents in parallel, run critic, then synthesize into a one-page brief."""
    config = _load_config()
    product_context = config["product_context"]

    # Phase 1: Run all 5 research agents in parallel
    company_intel, use_cases, stakeholders, objections, playbook = await asyncio.gather(
        research_company(company_name, role, product_context),
        research_use_cases(company_name, role, product_context),
        research_stakeholders(company_name, role, product_context),
        research_objections(company_name, role, product_context),
        research_playbook(company_name, role, product_context),
    )

    # Phase 2: Critic reviews all outputs
    critic_review = await review_outputs(
        company_name=company_name,
        role=role,
        company_intel=company_intel,
        use_cases=use_cases,
        stakeholders=stakeholders,
        objections=objections,
        playbook=playbook,
    )

    # Phase 3: Final synthesis incorporating critic feedback
    prompt = SYNTHESIS_PROMPT.format(
        company_intel=company_intel,
        use_cases=use_cases,
        stakeholders=stakeholders,
        objections=objections,
        playbook=playbook,
        critic_review=critic_review,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text


def _extract_section(text: str, header: str) -> str:
    """Extract content between a ## header and the next ## header."""
    marker = "## " + header
    start = text.find(marker)
    if start == -1:
        return ""
    start = start + len(marker)
    # Find next ## or end of string
    next_section = text.find("\n## ", start)
    if next_section == -1:
        return text[start:].strip()
    return text[start:next_section].strip()


async def update_plan(project_id: int) -> dict:
    """Load all call logs for a project, generate 7 outputs, and save them."""
    project = get_project(project_id)
    if not project:
        raise ValueError(f"Project {project_id} not found")

    logs = get_call_logs(project_id)
    if not logs:
        raise ValueError(f"No call logs found for project {project_id}")

    call_logs_text = "\n\n".join(
        f"**{log['date']}**\n{log['notes']}" for log in logs
    )

    prompt = PLAN_PROMPT.format(
        client_name=project["client_name"],
        industry=project["industry"],
        stage=project["stage"],
        call_logs=call_logs_text,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    full = response.content[0].text

    plan = save_plan(
        project_id=project_id,
        integration_map=_extract_section(full, "Integration Map"),
        stakeholder_tracker=_extract_section(full, "Stakeholder Tracker"),
        open_questions=_extract_section(full, "Open Questions"),
        risk_flags=_extract_section(full, "Risk Flags"),
        next_meeting_agenda=_extract_section(full, "Next Meeting Agenda"),
        technical_email=_extract_section(full, "Technical Follow-Up Email"),
        executive_email=_extract_section(full, "Executive Follow-Up Email"),
    )
    return plan
