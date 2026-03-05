"""Objection Agent - anticipates objections and prepares counterarguments."""

import asyncio
import os

import anthropic
from dotenv import load_dotenv
from tavily import TavilyClient

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
anthropic_client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are a technical pre-sales engineer who has handled hundreds of enterprise voice AI evaluations and knows every objection and how to address it.

This analysis will be used by a Forward Deployed Engineer at ElevenLabs preparing for a high-stakes enterprise client engagement. Accuracy matters more than comprehensiveness. Flag uncertainty rather than speculate."""

SYNTHESIS_PROMPT = """Product context for ElevenLabs (your company):
{product_context}

Based on the following search results about the prospect "{company_name}" and the target role "{role}", anticipate the objections a prospect would raise about adopting ElevenLabs voice AI technology.

Search results:

--- Competitors ---
{competitor_results}

--- Pricing ---
{pricing_results}

--- Limitations ---
{limitation_results}

Think step by step. First note what the search results reveal about this company's competitive landscape and potential concerns, then what is uncertain, then draw your conclusions about likely objections.

Return the top 4 objections a prospect is most likely to raise, each with:
- The objection stated clearly
- A suggested response tailored specifically to this company's product, positioning, and competitive landscape
- How strong this objection is likely to be (high/medium/low risk)

Make the responses practical and persuasive.

End with a brief "**Confidence note:**" flagging any areas where data was sparse, contradictory, or uncertain."""


async def _search(query: str) -> str:
    """Run a single Tavily search in a thread (Tavily client is synchronous)."""
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(
        f"- {result['title']}: {result['content']}" for result in response["results"]
    )


async def research_objections(company_name: str, role: str, product_context: str = "") -> str:
    """Research objections using parallel Tavily searches and Claude synthesis."""
    competitor_results, pricing_results, limitation_results = await asyncio.gather(
        _search(f"{company_name} competitors"),
        _search(f"{company_name} pricing"),
        _search(f"{company_name} limitations"),
    )

    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context,
        company_name=company_name,
        role=role,
        competitor_results=competitor_results,
        pricing_results=pricing_results,
        limitation_results=limitation_results,
    )

    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    return response.content[0].text
