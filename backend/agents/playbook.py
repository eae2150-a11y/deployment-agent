"""Playbook Agent - creates tactical engagement and deployment strategy."""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a senior implementation consultant who has delivered 50+ enterprise voice AI deployments.

This analysis will be used by a Forward Deployed Engineer at ElevenLabs preparing for a high-stakes enterprise client engagement. Accuracy matters more than comprehensiveness. Flag uncertainty rather than speculate."""

SYNTHESIS_PROMPT = """Product context for ElevenLabs (your company):
{product_context}

For the prospect "{company_name}" and the target role "{role}", generate a realistic 30/60/90 day deployment roadmap for integrating ElevenLabs voice AI technology.

Think step by step. First consider what you know about this company's likely technical environment and needs, then what is uncertain about their readiness, then design the roadmap accordingly.

Structure the roadmap as:

**Days 1-30: Foundation**
- 2-3 concrete milestones focused on initial setup, onboarding, and quick wins
- Specific ElevenLabs products/APIs to deploy first

**Days 31-60: Expansion**
- 2-3 concrete milestones focused on deeper integration, team adoption, and measurable results
- Key technical integrations to complete

**Days 61-90: Scale**
- 2-3 concrete milestones focused on full deployment, optimization, and proving ROI
- Success metrics and business outcomes to target

Make each milestone specific, actionable, and realistic for the given company and role. Include success metrics where possible.

End with a brief "**Confidence note:**" flagging any assumptions made about the company's technical environment or readiness."""


async def research_playbook(company_name: str, role: str, product_context: str = "") -> str:
    """Generate a 30/60/90 day deployment roadmap using Claude."""
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context,
        company_name=company_name,
        role=role,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
