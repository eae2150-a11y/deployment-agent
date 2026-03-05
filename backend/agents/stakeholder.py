"""Stakeholder Agent - identifies key decision-makers and organizational structure."""

import asyncio
import os

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an enterprise sales strategist who specializes in mapping buying committees and identifying champions vs blockers in complex B2B deals.

This analysis will be used by a Forward Deployed Engineer at ElevenLabs preparing for a high-stakes enterprise client engagement. Accuracy matters more than comprehensiveness. Flag uncertainty rather than speculate."""

SYNTHESIS_PROMPT = """Product context for ElevenLabs (your company):
{product_context}

Based on the following search results about the prospect "{company_name}" and the target role "{role}", map the key stakeholders involved in a purchasing decision for ElevenLabs voice AI technology.

Search results:

--- Customers ---
{customer_results}

--- Buyer Persona ---
{persona_results}

--- Enterprise Sales ---
{sales_results}

Think step by step. First note what the search results reveal about this company's organizational structure and decision-making, then what is uncertain, then draw your conclusions about the buying committee.

Identify and describe:
1. **Economic Buyer** — Who holds the budget and makes the final purchasing decision? What is their likely title and what do they care about?
2. **Day-to-Day Champion** — Who would be the internal advocate that uses and promotes the product daily? What motivates them?
3. **Likely Blocker** — Who is most likely to resist or block adoption? Why would they object, and what is their role?

Be specific to this company and role.

End with a brief "**Confidence note:**" flagging any areas where data was sparse, contradictory, or uncertain."""


async def _search(query: str) -> str:
    """Run a single Tavily search in a thread (Tavily client is synchronous)."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(
        f"- {result['title']}: {result['content']}" for result in response["results"]
    )


async def research_stakeholders(company_name: str, role: str, product_context: str = "") -> str:
    """Research stakeholders using parallel Tavily searches and Claude synthesis."""
    customer_results, persona_results, sales_results = await asyncio.gather(
        _search(f"{company_name} customers"),
        _search(f"{company_name} buyer persona"),
        _search(f"{company_name} enterprise sales"),
    )

    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context,
        company_name=company_name,
        role=role,
        customer_results=customer_results,
        persona_results=persona_results,
        sales_results=sales_results,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
