"""Playbook Agent - creates tactical engagement and deployment strategy."""

from backend.llm import chat

SYNTHESIS_PROMPT = """ElevenLabs context: {product_context}

For "{company_name}" (role: {role}), generate a 30/60/90 day deployment roadmap.

**Days 1-30: Foundation** - 2-3 milestones: setup, onboarding, quick wins. Which EL products first.
**Days 31-60: Expansion** - 2-3 milestones: deeper integration, team adoption, measurable results.
**Days 61-90: Scale** - 2-3 milestones: full deployment, optimization, ROI proof.

Be specific and actionable. Include success metrics.
End with "**Confidence note:**" on assumptions made."""


async def synthesize_playbook(company_name: str, role: str, product_context: str) -> str:
    """Claude-only: generate deployment roadmap (no Tavily needed)."""
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context, company_name=company_name, role=role,
    )
    return await chat(
        prompt=prompt, max_tokens=768,
        system="You are a senior implementation consultant with 50+ enterprise voice AI deployments.",
    )


async def research_playbook(company_name: str, role: str, product_context: str = "") -> str:
    return await synthesize_playbook(company_name, role, product_context)
