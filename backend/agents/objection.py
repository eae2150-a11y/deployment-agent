"""Objection Agent - anticipates objections and prepares counterarguments."""

import asyncio
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

SYNTHESIS_PROMPT = """ElevenLabs context: {product_context}

From search results about "{company_name}" (role: {role}), anticipate objections to adopting ElevenLabs voice AI.

{search_data}

Return top 4 objections with:
- The objection stated clearly
- Tailored response for this company
- Risk level (high/medium/low)

End with "**Confidence note:**" on uncertain areas."""


async def _search(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(f"- {r['title']}: {r['content']}" for r in response["results"])


async def fetch_objection_data(company_name: str) -> dict:
    """Tavily-only: fetch search data for objection research."""
    results = await asyncio.gather(
        _search(f"{company_name} competitors"),
        _search(f"{company_name} pricing"),
        _search(f"{company_name} limitations"),
    )
    return {"competitors": results[0], "pricing": results[1], "limitations": results[2]}


async def synthesize_objections(company_name: str, role: str, data: dict, product_context: str) -> str:
    """Claude-only: synthesize objection research."""
    search_data = "\n".join(f"--- {k.title()} ---\n{v}" for k, v in data.items())
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context, company_name=company_name,
        role=role, search_data=search_data,
    )
    return await chat(
        prompt=prompt, max_tokens=768,
        system="You are a technical pre-sales engineer. Be practical and persuasive.",
    )


async def research_objections(company_name: str, role: str, product_context: str = "") -> str:
    data = await fetch_objection_data(company_name)
    return await synthesize_objections(company_name, role, data, product_context)
