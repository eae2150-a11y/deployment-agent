"""Use Case Agent - identifies relevant deployment use cases for the target company."""

import asyncio
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

SYNTHESIS_PROMPT = """ElevenLabs context: {product_context}

From search results about "{company_name}" (role: {role}), identify the top 3 deployment use cases for ElevenLabs.

{search_data}

For each use case provide:
- Title
- One-sentence rationale (why high-impact and feasible)
- Which ElevenLabs product/API maps to it

End with "**Confidence note:**" on uncertain areas."""


async def _search(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(f"- {r['title']}: {r['content']}" for r in response["results"])


async def fetch_use_case_data(company_name: str, role: str) -> dict:
    """Tavily-only: fetch search data for use case research."""
    results = await asyncio.gather(
        _search(f"{company_name} use cases"),
        _search(f"{company_name} enterprise customers"),
        _search(f"{company_name} {role} workflow"),
    )
    return {"use_cases": results[0], "customers": results[1], "workflow": results[2]}


async def synthesize_use_cases(company_name: str, role: str, data: dict, product_context: str) -> str:
    """Claude-only: synthesize use case research."""
    search_data = "\n".join(f"--- {k.replace('_', ' ').title()} ---\n{v}" for k, v in data.items())
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context, company_name=company_name,
        role=role, search_data=search_data,
    )
    return await chat(
        prompt=prompt, max_tokens=768,
        system="You are a voice AI solutions architect. Be actionable and specific.",
    )


async def research_use_cases(company_name: str, role: str, product_context: str = "") -> str:
    data = await fetch_use_case_data(company_name, role)
    return await synthesize_use_cases(company_name, role, data, product_context)
