"""Company Intel Agent - researches company background, products, news, and tech stack."""

import asyncio
import os

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a senior industry analyst specializing in AI company research and enterprise technology adoption.

This analysis will be used by a Forward Deployed Engineer at ElevenLabs preparing for a high-stakes enterprise client engagement. Accuracy matters more than comprehensiveness. Flag uncertainty rather than speculate."""

SYNTHESIS_PROMPT = """Product context for ElevenLabs (your company):
{product_context}

Based on the following search results about the prospect "{company_name}", produce a concise intelligence summary.

Search results:

--- AI/Startup Profile ---
{ai_results}

--- Product & Customers ---
{product_results}

--- Funding News ---
{funding_results}

Think step by step. First note what you know with confidence from the search results, then what is uncertain or missing, then draw your conclusions.

Write a summary covering:
1. What the company does (core mission and business)
2. Their main product or service offering
3. Who their customers are (target market, notable clients)
4. Their funding stage and financial backing
5. Their tech/AI maturity (how advanced their tech stack and AI capabilities are)

Keep it factual, concise, and useful for a sales engagement.

End with a brief "**Confidence note:**" flagging any areas where data was sparse, contradictory, or uncertain."""


async def _search(query: str) -> str:
    """Run a single Tavily search in a thread (Tavily client is synchronous)."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(
        f"- {result['title']}: {result['content']}" for result in response["results"]
    )


async def research_company(company_name: str, role: str, product_context: str = "") -> str:
    """Research a company using parallel Tavily searches and Claude synthesis."""
    ai_results, product_results, funding_results = await asyncio.gather(
        _search(f"{company_name} AI startup"),
        _search(f"{company_name} product customers"),
        _search(f"{company_name} funding news"),
    )

    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context,
        company_name=company_name,
        ai_results=ai_results,
        product_results=product_results,
        funding_results=funding_results,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
