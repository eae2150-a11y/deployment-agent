"""Use Case Agent - identifies relevant AI/deployment use cases for the target company."""

import asyncio
import os

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a voice AI solutions architect with deep expertise in ElevenLabs products and enterprise deployment patterns.

This analysis will be used by a Forward Deployed Engineer at ElevenLabs preparing for a high-stakes enterprise client engagement. Accuracy matters more than comprehensiveness. Flag uncertainty rather than speculate."""

SYNTHESIS_PROMPT = """Product context for ElevenLabs (your company):
{product_context}

Based on the following search results about the prospect "{company_name}" and the target role "{role}", identify the best deployment use cases for ElevenLabs technology.

Search results:

--- Use Cases ---
{use_case_results}

--- Enterprise Customers ---
{customer_results}

--- Role Workflow ---
{workflow_results}

Think step by step. First note what you know with confidence about this company's workflows and needs, then what is uncertain, then draw your conclusions about the best use cases.

Return the top 3 deployment use cases ranked by ease of implementation and business impact. For each use case, provide:
- A clear title
- A one-sentence rationale explaining why this use case is high-impact and feasible for this company
- Which specific ElevenLabs product/API maps to this use case

Keep it actionable and specific to this company.

End with a brief "**Confidence note:**" flagging any areas where data was sparse, contradictory, or uncertain."""


async def _search(query: str) -> str:
    """Run a single Tavily search in a thread (Tavily client is synchronous)."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(
        f"- {result['title']}: {result['content']}" for result in response["results"]
    )


async def research_use_cases(company_name: str, role: str, product_context: str = "") -> str:
    """Research use cases using parallel Tavily searches and Claude synthesis."""
    use_case_results, customer_results, workflow_results = await asyncio.gather(
        _search(f"{company_name} use cases"),
        _search(f"{company_name} enterprise customers"),
        _search(f"{company_name} {role} workflow"),
    )

    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context,
        company_name=company_name,
        role=role,
        use_case_results=use_case_results,
        customer_results=customer_results,
        workflow_results=workflow_results,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
