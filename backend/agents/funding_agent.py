"""Funding Agent - detects funding rounds, growth signals, and timing indicators."""

import asyncio
import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

FUNDING_PROMPT = """Analyze search results for "{company_name}" and extract funding/growth intelligence.

Look for: recent funding round (amount, date, series, investors), total raised, headcount, geographic expansion, product launches, revenue milestones, layoffs (negative signal).

{search_data}

Return ONLY valid JSON:
{{
  "latest_funding": {{
    "amount": "dollar amount or 'Unknown'",
    "series": "stage or 'Unknown'",
    "date": "month/year or 'Unknown'",
    "investors": ["investors if found"]
  }},
  "total_funding": "total or 'Unknown'",
  "headcount_estimate": "range or 'Unknown'",
  "growth_signals": ["concise sentences on buying-timing implications"],
  "why_now_score": 0-100,
  "why_now_summary": "2-3 sentences on timing"
}}

Score: 80-100 recent large funding + expansion, 60-79 recent funding or strong growth, 40-59 uncertain, 20-39 stable but not investing, 0-19 negative signals or no data."""


async def _search(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(f"- {r['title']}: {r['content']}" for r in response["results"])


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def fetch_funding_data(company_name: str) -> dict:
    """Tavily-only: fetch funding and growth search data."""
    results = await asyncio.gather(
        _search(f"{company_name} funding raised series 2024 2025"),
        _search(f"{company_name} headcount growth employees 2024 2025"),
    )
    return {"funding": results[0], "growth": results[1]}


async def synthesize_funding_signals(company_name: str, data: dict) -> dict:
    """Claude-only: analyze funding data and return structured signals."""
    search_data = "\n".join(f"--- {k.title()} ---\n{v}" for k, v in data.items())
    prompt = FUNDING_PROMPT.format(company_name=company_name, search_data=search_data)
    text = await chat(
        prompt=prompt, max_tokens=512,
        system="Return only valid JSON, no markdown.",
    )
    try:
        return json.loads(_strip_fences(text))
    except json.JSONDecodeError:
        return {
            "latest_funding": {"amount": "Unknown", "series": "Unknown", "date": "Unknown", "investors": []},
            "total_funding": "Unknown", "headcount_estimate": "Unknown",
            "growth_signals": [], "why_now_score": 0,
            "why_now_summary": "Unable to parse funding results.",
        }


async def detect_funding_signals(company_name: str) -> dict:
    data = await fetch_funding_data(company_name)
    return await synthesize_funding_signals(company_name, data)
