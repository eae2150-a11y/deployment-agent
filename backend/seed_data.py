"""Seed data: pre-populate a realistic Gorillas demo project."""

import json

from backend.database import create_project, add_call_log, list_projects

GORILLAS_BRIEF = """# Gorillas — ElevenLabs Deployment Brief

## Company Overview
Gorillas is a last-mile grocery delivery company operating across Germany, Netherlands, UK, and France. They manage ~15,000 riders and process millions of deliveries per month. Their operations are heavily phone-dependent — rider onboarding, dark store coordination, and customer support all rely on voice workflows currently handled through Twilio Flex.

## Product Fit: Conversational AI (ElevenAgents)
Gorillas' rider operations workflows are a textbook fit for ElevenAgents. Their highest-volume voice use case — rider re-engagement after failed onboarding — is repetitive, scriptable, and currently handled by human agents. The Deliveroo case study (30% re-engagement rate, 75% restaurant verification success) maps directly to Gorillas' operational model.

## Secondary Opportunity: TTS API
Outbound delivery notifications (ETA updates, substitution confirmations) could replace SMS with personalized voice calls at scale, improving customer experience in all 4 markets.

## Technical Fit
- **Architecture:** Advanced Cascaded (Scribe v2 Realtime STT + LLM reasoning + EL TTS Expressive Mode)
- **Why cascaded:** Rider ops workflows require tool-use (querying rider status API, updating onboarding records) — fused models sacrifice the guardrails and tool integration Gorillas needs
- **Model:** Eleven Turbo v2.5 for ultra-low latency — riders on mobile need instant response
- **Integration:** Native Twilio integration means EL plugs into their existing Twilio Flex stack — no rip-and-replace
- **Migration complexity:** Low — they have no existing voice AI to displace

## Competitive Landscape
- **No incumbent voice AI** — this is a greenfield opportunity
- **Winning angle:** No competitor displacement needed; lead with speed-to-deployment and Twilio compatibility
- **What NOT to lead with:** Don't emphasize voice quality/naturalness to ops teams — they care about reliability, integration speed, and measurable operational outcomes

## Top Use Cases
1. **Rider re-engagement:** Automated outbound calls to riders who haven't completed onboarding after 7 days
2. **Dark store verification:** Inbound calls from store operators to verify order status, report issues
3. **Delivery ETA notifications:** Proactive voice calls to customers with real-time delivery updates

## Key Stakeholders
- **Maria Schmidt** (Head of Rider Ops) — Champion. Immediately resonated with Deliveroo comparison. Decision-maker for ops tooling.
- **Jonas Weber** (CTO) — Technical sponsor. Confirmed Twilio Flex stack. Needs to sign off on infrastructure changes.
- **Stefan Muller** (Lead Backend Engineer) — Technical implementer. Building the rider status API endpoint for agent integration. Setting up sandbox Twilio environment.

## Why Now
- Series B: EUR 290M raised — budget available for infrastructure investment
- Expanding to 3 new cities — scaling ops team, need automation to maintain quality
- Hiring 3 Rider Operations Managers + Customer Support Lead — exactly the roles that would own/benefit from voice automation

## Likely Objections & Responses
1. **GDPR/data residency:** ElevenLabs offers EU data residency. Confirmed in technical deep-dive with Jonas.
2. **Reliability at scale:** ElevenAgents handles millions of calls. Start with 500-rider Berlin cohort to prove reliability before full rollout.

## 30/60/90 Day Playbook
- **Day 1-14:** POC — rider re-engagement agent, Berlin cohort, 500 riders, German voice only
- **Day 15-45:** Expand to dark store verification, add English voice, measure operational impact
- **Day 45-90:** Roll out to all 4 markets, localised voices, integrate ETA notification use case

## Opening Pitch
"You're hiring 3 Rider Operations Managers right now — the workflows they'll inherit are exactly what ElevenAgents automates. Deliveroo saw 30% rider re-engagement and 75% store verification success with the same architecture. Your Twilio Flex stack means we can be live in days, not months."

## Watch Out
- CTO sign-off required for any infrastructure change — keep Jonas engaged
- GDPR sensitivity is high — always lead with EU data residency in every conversation
- POC success metrics must be clearly defined before launch to avoid ambiguity"""

GORILLAS_PRODUCT_MATCH = {
    "primary_product": "Conversational AI (ElevenAgents)",
    "primary_reason": "High-volume rider ops workflows (onboarding re-engagement, store verification) are textbook voice agent use cases. Deliveroo achieved 30% re-engagement — same playbook applies.",
    "integration_pattern": "Scribe v2 Realtime STT + LLM reasoning + EL TTS Expressive Mode",
    "why_not_fused": "Rider ops workflows require tool-use (querying rider status API, updating records mid-call) — fused models sacrifice guardrails and tool integration",
    "existing_stack_conflict": "Currently on Twilio Flex with no voice AI. EL plugs in via native Twilio integration — complement, not replacement.",
    "migration_complexity": "low",
    "migration_reason": "No existing voice AI to displace. Twilio integration is native — days not months.",
    "recommended_model": "Eleven Turbo v2.5",
    "recommended_architecture": "Advanced Cascaded",
    "scribe_v2_realtime_relevant": True,
    "secondary_product": "TTS API",
    "secondary_reason": "Outbound delivery ETA notifications in 4 languages — replace SMS with personalised voice at scale",
    "fit_score": 87,
    "fit_tier": "Hot",
    "fit_rationale": "Greenfield voice AI opportunity with proven comparable (Deliveroo), strong champion, active budget from Series B, and native Twilio stack compatibility.",
    "likely_competitors": [],
    "competitive_risk": "None detected — greenfield opportunity, no incumbent voice AI",
    "competitive_angle": "No competitor to displace — lead with speed-to-deployment and Twilio compatibility",
    "key_objection": "GDPR compliance and EU data residency requirements",
    "winning_angle": "Deliveroo case study + native Twilio integration + Series B budget = fastest path to operational impact",
}

GORILLAS_SIGNALS = {
    "company_name": "Gorillas",
    "website": "gorillas.io",
    "signals_detected": ["customer_facing_comms", "multilingual", "high_content_volume"],
    "current_audio_tools": ["Twilio Flex"],
    "evidence": [
        "Operates in 4 markets: Germany, Netherlands, UK, France",
        "~15,000 riders managed via phone-based ops workflows",
        "Millions of deliveries per month requiring real-time coordination",
        "Twilio Flex used for rider and customer support telephony",
    ],
    "employee_count_estimate": "1000-2000",
    "industry": "Last-mile grocery delivery",
    "existing_voice_stack": ["Twilio"],
    "is_api_first": True,
    "needs_realtime": True,
    "operates_at_scale": True,
    "language_count": 4,
}

GORILLAS_JOB_SIGNALS = {
    "jobs_found": [
        {
            "title": "Rider Operations Manager",
            "product_signal": "Conversational AI",
            "intent_level": "high",
            "greenfield_or_migration": "greenfield",
            "seniority": "manager",
            "implication": "Scaling rider ops team — voice automation would directly multiply their impact",
            "source_url": "",
            "posted_date": "2026-02",
        },
        {
            "title": "Rider Operations Manager",
            "product_signal": "Conversational AI",
            "intent_level": "high",
            "greenfield_or_migration": "greenfield",
            "seniority": "manager",
            "implication": "Second hire in same role — indicates significant ops expansion",
            "source_url": "",
            "posted_date": "2026-02",
        },
        {
            "title": "Rider Operations Manager",
            "product_signal": "Conversational AI",
            "intent_level": "high",
            "greenfield_or_migration": "greenfield",
            "seniority": "manager",
            "implication": "Third hire — likely one per new city expansion",
            "source_url": "",
            "posted_date": "2026-02",
        },
        {
            "title": "Customer Support Lead",
            "product_signal": "Conversational AI",
            "intent_level": "medium",
            "greenfield_or_migration": "greenfield",
            "seniority": "manager",
            "implication": "Building out support function — voice AI can deflect Tier 1 volume",
            "source_url": "",
            "posted_date": "2026-01",
        },
    ],
    "top_signal": "Hiring 3x Rider Operations Managers + Customer Support Lead — scaling the exact teams that would benefit from voice automation",
    "intent_score": 78,
}

GORILLAS_FUNDING_SIGNALS = {
    "latest_funding": {
        "amount": "\u20ac290M",
        "series": "Series B",
        "date": "2025",
        "investors": [],
    },
    "total_funding": "\u20ac290M+",
    "headcount_estimate": "1000-2000",
    "growth_signals": [
        "Expanding to 3 new cities in 2026",
        "Series B provides budget for infrastructure investment",
        "Actively hiring ops and support leadership roles",
    ],
    "why_now_score": 76,
    "why_now_summary": "Recent Series B (\u20ac290M) funds infrastructure investment. Expanding to 3 new cities creates immediate need to scale ops without proportional headcount growth. Voice automation is the lever.",
}

GORILLAS_IMPL_PLAN = {
    "phase_1": "\u2022 Build rider re-engagement voice agent using ElevenAgents + Twilio integration\n\u2022 Target: riders who haven't completed onboarding after 7 days\n\u2022 Scope: 500 riders in Berlin cohort, German voice only\n\u2022 Stack: ElevenAgents platform (no-code), Turbo v2.5, German + English voices\n\u2022 Success criteria: reach 80% of target cohort, 25%+ continue onboarding",
    "phase_2": "\u2022 Expand to dark store status verification calls (Deliveroo-proven pattern)\n\u2022 Stack: Twilio webhook \u2192 ElevenAgents \u2192 real-time order system update\n\u2022 Language routing: detect caller locale, switch voice automatically (DE/EN/NL/FR)\n\u2022 Auth: API key server-side for agent backend, single-use tokens for any web widget\n\u2022 Edge cases: failed calls \u2192 SMS fallback, voicemail detection, silence timeouts",
    "phase_3": "\u2022 Roll out to all 4 markets with localised voices per region\n\u2022 Add ElevenAgents analytics dashboard for ops team KPIs (call completion, re-engagement rate)\n\u2022 Explore outbound delivery ETA notification use case (voice replaces SMS)\n\u2022 Voice consistency: lock voice IDs per market, version-control in CI/CD\n\u2022 Quarterly model review cadence as EL releases new model versions",
}

GORILLAS_CALL_LOGS = [
    {
        "date": "2026-02-12",
        "notes": "Intro call with Maria Schmidt (Head of Rider Ops) and Jonas Weber (CTO). Maria immediately resonated with the Deliveroo comparison \u2014 asked for the case study. Jonas asked about Twilio compatibility, confirmed they're on Twilio Flex. Agreed to run a POC on the rider re-engagement use case. Jonas will loop in their lead backend engineer next call.",
    },
    {
        "date": "2026-02-24",
        "notes": "Technical deep dive with Jonas + Stefan M\u00fcller (Lead Backend Engineer). Walked through the ElevenAgents + Twilio webhook integration. Stefan confirmed they can expose a rider status API endpoint for the agent to query. Concern raised about GDPR \u2014 confirmed EL has EU data residency. POC scope agreed: 500 riders in Berlin cohort, German voice only. Stefan to set up a sandbox Twilio number by end of week.",
    },
    {
        "date": "2026-03-03",
        "notes": "POC kickoff with Stefan. ElevenAgents configured, Turbo v2.5 selected, German voice approved by Maria. First test calls went live \u2014 latency under 100ms, voice quality sign-off from ops team. Minor issue: voicemail detection triggering too early, EL support flagged a config fix. On track for first cohort results by March 10.",
    },
]

GORILLAS_NEXT_ACTION = "Follow up March 10 on POC cohort results \u2014 Maria to share rider re-engagement data. Prepare Phase 2 proposal (dark store verification) for review."


def seed_gorillas() -> None:
    """Create the Gorillas demo project if no projects exist."""
    projects = list_projects()
    if projects:
        return

    brief_data = json.dumps({
        "company": "Gorillas",
        "brief": GORILLAS_BRIEF,
        "product_match": GORILLAS_PRODUCT_MATCH,
        "signals": GORILLAS_SIGNALS,
        "job_signals": GORILLAS_JOB_SIGNALS,
        "funding_signals": GORILLAS_FUNDING_SIGNALS,
        "implementation_plan": GORILLAS_IMPL_PLAN,
    })

    project = create_project(
        client_name="Gorillas",
        industry="Last-mile grocery delivery",
        stage="POC Active",
        brief_data=brief_data,
    )

    for log_entry in GORILLAS_CALL_LOGS:
        add_call_log(project["id"], log_entry["date"], log_entry["notes"])
