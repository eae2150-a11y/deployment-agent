"""Critic Agent - reviews all agent outputs for contradictions, weak reasoning, and gaps."""

from backend.llm import chat

REVIEW_PROMPT = """Review these 5 research outputs for "{company_name}" (role: {role}).

Flag briefly:
1. **Contradictions** between agents
2. **Weak reasoning** - poorly supported claims
3. **Critical gaps** the synthesis should call out
4. **Confidence** - any agent overconfident given sparse data?

Be concise. Reference which agent has each issue.

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
        company_name=company_name, role=role,
        company_intel=company_intel, use_cases=use_cases,
        stakeholders=stakeholders, objections=objections,
        playbook=playbook,
    )
    return await chat(
        prompt=prompt, max_tokens=512,
        system="You are a QA reviewer. Find real problems, be direct. Don't invent issues.",
    )
