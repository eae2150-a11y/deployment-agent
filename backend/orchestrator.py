"""Orchestrator that runs research agents in phases to avoid rate limits."""

import asyncio
import json
import logging
import os

from dotenv import load_dotenv

from backend.llm import chat
from backend.agents.company_intel import (
    fetch_signal_data, synthesize_signals,
    fetch_company_data, synthesize_company,
)
from backend.agents.job_signal_agent import fetch_job_data, synthesize_job_signals
from backend.agents.funding_agent import fetch_funding_data, synthesize_funding_signals
from backend.agents.use_case import fetch_use_case_data, synthesize_use_cases
from backend.agents.stakeholder import fetch_stakeholder_data, synthesize_stakeholders
from backend.agents.objection import fetch_objection_data, synthesize_objections
from backend.agents.playbook import synthesize_playbook
from backend.agents.el_product_agent import match_products
from backend.agents.critic import review_outputs
from backend.database import get_call_logs, get_project, save_plan

load_dotenv()

log = logging.getLogger(__name__)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "configs", "elevenlabs.json")

# Delay between sequential Claude calls to stay under rate limits
CLAUDE_STAGGER_DELAY = 2.0


def _load_config() -> dict:
    with open(CONFIG_PATH) as f:
        return json.load(f)


SYNTHESIS_PROMPT = """You are an ElevenLabs FDE preparing a one-page prospect brief.

Write these sections using the data below. Reference specific evidence. Position {primary_product} specifically, not ElevenLabs generically. The "Why Now" section MUST cite job postings and funding data.

1. **Company Overview**
2. **Product Fit: {primary_product}** - why it fits, with evidence
3. **Secondary Opportunity: {secondary_product}**
4. **Technical Fit** - recommended product + integration pattern, architecture, migration complexity, existing stack interaction, model recommendation. If Scribe v2 Realtime is relevant, call it out.
5. **Competitive Landscape** - most likely competitor they're evaluating, one-line winning angle vs that competitor, what NOT to lead with
6. **Top Use Cases** - 3 most actionable
7. **Key Stakeholders**
8. **Why Now** - cite jobs, funding, expansion for urgency
9. **Likely Objections & Responses** - top 2-3
10. **30/60/90 Day Playbook**
11. **Opening Pitch** - 2-3 sentences with specific evidence
12. **Watch Out** - low-confidence areas from critic

--- Product Match ---
{primary_product} (Score: {fit_score}/100 — {fit_tier}): {primary_reason}
Secondary: {secondary_product}: {secondary_reason}
Angle: {winning_angle} | Objection: {key_objection} | Competitors: {likely_competitors}

--- Technical Architecture ---
Integration Pattern: {integration_pattern}
Recommended Architecture: {recommended_architecture}
Recommended Model: {recommended_model}
Migration Complexity: {migration_complexity} — {migration_reason}
Existing Stack Conflict: {existing_stack_conflict}
Why Not Fused: {why_not_fused}
Scribe v2 Realtime Relevant: {scribe_v2_realtime_relevant}

--- Competitive Intel ---
Primary Risk: {competitive_risk}
Winning Angle: {competitive_angle}

--- Job Signals ({intent_score}/100) ---
{job_top_signal}
{job_listings}

--- Funding ({why_now_score}/100) ---
{latest_funding} | Total: {total_funding} | Headcount: {headcount_estimate}
{growth_signals}
{why_now_summary}

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

--- Critic ---
{critic_review}

--- User Notes ---
{user_notes}"""


PLAN_PROMPT = """You are an ElevenLabs FDE managing a client project.

Client: {client_name} ({industry}) | Stage: {stage}

Call logs:
{call_logs}

Produce 7 sections from what was actually discussed (don't invent):

## Integration Map
Systems, APIs, data flows, dependencies discussed.

## Stakeholder Tracker
People mentioned: name, role, champion/neutral/blocker, key quotes.

## Open Questions
Unanswered items grouped by category.

## Risk Flags
Deal risks with severity (High/Medium/Low) and mitigation.

## Next Meeting Agenda
3-5 questions, talking points, risks to address.

## Technical Follow-Up Email
To technical contact. Start with "Subject:".

## Executive Follow-Up Email
To exec sponsor, business value focus. Start with "Subject:"."""


async def run_all_agents(company_name: str, role: str, user_notes: str = "") -> dict:
    """Run research pipeline in phases to stay under rate limits.

    Phase 1 (parallel, Tavily only): all data fetching
    Phase 2 (sequential, Claude): signal synthesis -> product match -> research synthesis -> critic -> final brief
    """
    config = _load_config()
    product_context = config["product_context"]

    # ── Phase 1: All Tavily fetches in parallel (no Claude calls) ──
    log.info("Phase 1: fetching all search data in parallel")
    (
        signal_data, company_data, job_data, funding_data,
        use_case_data, stakeholder_data, objection_data,
    ) = await asyncio.gather(
        fetch_signal_data(company_name),
        fetch_company_data(company_name),
        fetch_job_data(company_name),
        fetch_funding_data(company_name),
        fetch_use_case_data(company_name, role),
        fetch_stakeholder_data(company_name, role),
        fetch_objection_data(company_name),
    )

    # ── Phase 2: Sequential Claude calls with stagger delays ──
    log.info("Phase 2: running Claude synthesis calls sequentially")

    # 2a: Signal detection + job signals + funding signals (structured JSON extraction)
    signals = await synthesize_signals(company_name, signal_data)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    job_signals = await synthesize_job_signals(company_name, job_data)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    funding_signals = await synthesize_funding_signals(company_name, funding_data)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    # 2b: Product matching (needs signals)
    enriched_signals = dict(signals)
    if job_signals.get("intent_score", 0) > 0:
        job_products = [j.get("product_signal", "") for j in job_signals.get("jobs_found", [])]
        enriched_signals["job_product_signals"] = job_products
    if funding_signals.get("why_now_score", 0) > 50:
        enriched_signals.setdefault("evidence", []).append(
            f"Funding signal: {funding_signals.get('why_now_summary', '')}"
        )

    product_match = await match_products(company_name, enriched_signals, user_notes)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    # Adjust fit_score based on job intent and funding signals
    base_score = product_match.get("fit_score", 0)
    intent_score = job_signals.get("intent_score", 0)
    why_now_score = funding_signals.get("why_now_score", 0)
    boost = int((intent_score * 0.08) + (why_now_score * 0.07))
    adjusted_score = min(100, base_score + boost)
    product_match["fit_score"] = adjusted_score
    if adjusted_score >= 70:
        product_match["fit_tier"] = "Hot"
    elif adjusted_score >= 45:
        product_match["fit_tier"] = "Warm"
    else:
        product_match["fit_tier"] = "Cold"

    # 2c: Research synthesis (5 agents, run sequentially)
    company_intel = await synthesize_company(company_name, company_data, product_context)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    use_cases = await synthesize_use_cases(company_name, role, use_case_data, product_context)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    stakeholders = await synthesize_stakeholders(company_name, role, stakeholder_data, product_context)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    objections = await synthesize_objections(company_name, role, objection_data, product_context)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    playbook = await synthesize_playbook(company_name, role, product_context)
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    # 2d: Critic review
    critic_review = await review_outputs(
        company_name=company_name, role=role,
        company_intel=company_intel, use_cases=use_cases,
        stakeholders=stakeholders, objections=objections,
        playbook=playbook,
    )
    await asyncio.sleep(CLAUDE_STAGGER_DELAY)

    # 2e: Final synthesis
    job_listings = "\n".join(
        f"- {j.get('title', '?')} ({j.get('intent_level', 'low')}) -> {j.get('product_signal', '?')}"
        for j in job_signals.get("jobs_found", [])
    ) or "No relevant job postings found"

    latest_funding = funding_signals.get("latest_funding", {})
    latest_funding_str = (
        f"{latest_funding.get('series', '?')} — {latest_funding.get('amount', '?')} "
        f"({latest_funding.get('date', '?')})"
        if latest_funding.get("amount", "Unknown") != "Unknown"
        else "No recent funding data"
    )

    growth_signals_str = "\n".join(
        f"- {s}" for s in funding_signals.get("growth_signals", [])
    ) or "None detected"

    prompt = SYNTHESIS_PROMPT.format(
        company_intel=company_intel, use_cases=use_cases,
        stakeholders=stakeholders, objections=objections,
        playbook=playbook, critic_review=critic_review,
        primary_product=product_match.get("primary_product", "Unknown"),
        secondary_product=product_match.get("secondary_product", "Unknown"),
        fit_score=product_match.get("fit_score", 0),
        fit_tier=product_match.get("fit_tier", "Unknown"),
        primary_reason=product_match.get("primary_reason", ""),
        secondary_reason=product_match.get("secondary_reason", ""),
        winning_angle=product_match.get("winning_angle", ""),
        key_objection=product_match.get("key_objection", ""),
        likely_competitors=", ".join(product_match.get("likely_competitors", [])),
        integration_pattern=product_match.get("integration_pattern", ""),
        recommended_architecture=product_match.get("recommended_architecture", "REST batch"),
        recommended_model=product_match.get("recommended_model", "Eleven Multilingual v2"),
        migration_complexity=product_match.get("migration_complexity", "medium"),
        migration_reason=product_match.get("migration_reason", ""),
        existing_stack_conflict=product_match.get("existing_stack_conflict", ""),
        why_not_fused=product_match.get("why_not_fused", ""),
        scribe_v2_realtime_relevant=product_match.get("scribe_v2_realtime_relevant", False),
        competitive_risk=product_match.get("competitive_risk", ""),
        competitive_angle=product_match.get("competitive_angle", ""),
        intent_score=intent_score,
        job_top_signal=job_signals.get("top_signal", "No job signals"),
        job_listings=job_listings,
        why_now_score=why_now_score,
        latest_funding=latest_funding_str,
        total_funding=funding_signals.get("total_funding", "Unknown"),
        headcount_estimate=funding_signals.get("headcount_estimate", "Unknown"),
        growth_signals=growth_signals_str,
        why_now_summary=funding_signals.get("why_now_summary", "No timing signals"),
        user_notes=user_notes or "None provided",
    )

    brief = await chat(prompt=prompt, max_tokens=2048)

    return {
        "brief": brief,
        "signals": signals,
        "product_match": product_match,
        "job_signals": job_signals,
        "funding_signals": funding_signals,
    }


def _extract_section(text: str, header: str) -> str:
    """Extract content between a ## header and the next ## header."""
    marker = "## " + header
    start = text.find(marker)
    if start == -1:
        return ""
    start = start + len(marker)
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

    full = await chat(prompt=prompt, max_tokens=4096)

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
