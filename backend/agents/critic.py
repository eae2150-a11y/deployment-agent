"""Critic Agent - reviews all agent outputs for contradictions, weak reasoning, and gaps."""

import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a rigorous internal reviewer and quality assurance analyst for an enterprise sales intelligence team.

Your job is to find problems before they reach the client-facing brief. Be direct and specific. If everything looks solid, say so briefly — do not invent issues."""

REVIEW_PROMPT = """Below are 5 research outputs prepared for an ElevenLabs Forward Deployed Engineer ahead of an enterprise engagement with "{company_name}" (target role: {role}).

Review all 5 outputs and produce a brief quality report covering:

1. **Contradictions** — Do any agents contradict each other? (e.g., one says the company is early-stage while another assumes enterprise maturity)
2. **Weak reasoning** — Are any conclusions poorly supported or based on thin evidence? Flag specific claims.
3. **Critical gaps** — What important information is missing that the synthesis should be careful about or call out?
4. **Confidence assessment** — Review each agent's confidence note. Are they appropriately calibrated, or is any agent overconfident given sparse data?

Be concise and specific. Reference which agent output contains each issue.

--- Company Intel ---
{company_intel}

--- Use Cases ---
{use_cases}

--- Stakeholders ---
{stakeholders}

--- Objections ---
{objections}

--- Playbook ---
{playbook}"""


async def review_outputs(
    company_name: str,
    role: str,
    company_intel: str,
    use_cases: str,
    stakeholders: str,
    objections: str,
    playbook: str,
) -> str:
    """Review all 5 agent outputs and flag issues for the synthesis step."""
    prompt = REVIEW_PROMPT.format(
        company_name=company_name,
        role=role,
        company_intel=company_intel,
        use_cases=use_cases,
        stakeholders=stakeholders,
        objections=objections,
        playbook=playbook,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
