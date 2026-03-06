"""Stakeholder Agent - identifies key decision-makers and organizational structure."""

import asyncio
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

SYNTHESIS_PROMPT = """ElevenLabs context: {product_context}

From search results about "{company_name}" (role: {role}), map the buying committee for ElevenLabs voice AI.

{search_data}

Identify:
1. **Economic Buyer** - Who holds budget? Title and priorities.
2. **Champion** - Internal advocate who uses/promotes the product daily.
3. **Likely Blocker** - Who resists adoption and why.

Be specific to this company. End with "**Confidence note:**" on uncertain areas."""


async def _search(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(f"- {r['title']}: {r['content']}" for r in response["results"])


async def fetch_stakeholder_data(company_name: str, role: str) -> dict:
    """Tavily-only: fetch search data for stakeholder research."""
    results = await asyncio.gather(
        _search(f"{company_name} customers"),
        _search(f"{company_name} buyer persona"),
        _search(f"{company_name} enterprise sales"),
    )
    return {"customers": results[0], "persona": results[1], "sales": results[2]}


async def synthesize_stakeholders(company_name: str, role: str, data: dict, product_context: str) -> str:
    """Claude-only: synthesize stakeholder research."""
    search_data = "\n".join(f"--- {k.title()} ---\n{v}" for k, v in data.items())
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context, company_name=company_name,
        role=role, search_data=search_data,
    )
    return await chat(
        prompt=prompt, max_tokens=768,
        system="You are an enterprise sales strategist. Map buying committees and identify champions vs blockers.",
    )


async def research_stakeholders(company_name: str, role: str, product_context: str = "") -> str:
    data = await fetch_stakeholder_data(company_name, role)
    return await synthesize_stakeholders(company_name, role, data, product_context)
