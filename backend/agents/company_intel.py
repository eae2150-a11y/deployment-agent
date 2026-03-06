"""Company Intel Agent - scans websites and searches for signals relevant to ElevenLabs products."""

import asyncio
import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

SIGNAL_DETECTION_PROMPT = """Analyze search results about "{company_name}" and detect ElevenLabs product-fit signals.

PRODUCT-FIT SIGNALS (only if concrete evidence):
- has_audio_video: audio/video content (podcast, video demos, webinars)
- multilingual: multilingual site/content (language selectors, hreflang, multi-language content)
- high_content_volume: active blog, knowledge base, documentation, help center
- customer_facing_comms: support center, IVR, notifications, voicemail, call center
- developer_api: /docs, /api, developer portal, SDK
- media_entertainment: publishing, games, streaming, content creation

TECHNICAL STACK SIGNALS (detect from site/docs/job posts):
- existing_voice_stack: look for mentions of Twilio, Amazon Polly, Google TTS, Azure Cognitive, Murf, Deepgram, AssemblyAI, Resemble, Play.ht, WellSaid, Nuance, or any voice/TTS vendor
- is_api_first: /docs page exists, developer portal, SDK mentions, webhook references, API-first architecture
- needs_realtime: mentions of "live", "streaming", "low latency", "real-time", "WebSocket"
- operates_at_scale: "millions of users", "enterprise", "contact center", "IVR", "outbound", high-volume indicators
- language_count: count of languages from hreflang tags, language selectors, /en/ /es/ /fr/ URL patterns, "available in X languages"

{search_data}

Return ONLY valid JSON:
{{
  "company_name": "{company_name}",
  "website": "best URL found or empty string",
  "signals_detected": ["product-fit signal keys detected"],
  "current_audio_tools": ["audio/voice/TTS tools or competitors found"],
  "evidence": ["one supporting quote per signal"],
  "employee_count_estimate": "estimate or 'Unknown'",
  "industry": "primary industry",
  "existing_voice_stack": ["vendor names found in their stack, e.g. Twilio, Amazon Polly"],
  "is_api_first": true or false,
  "needs_realtime": true or false,
  "operates_at_scale": true or false,
  "language_count": number or 0 if unknown
}}"""

SYNTHESIS_PROMPT = """ElevenLabs context: {product_context}

From search results about "{company_name}", write a concise intel summary:
1. What they do (mission/business)
2. Main product/service
3. Target customers and notable clients
4. Funding stage
5. Tech/AI maturity

{search_data}

Be factual and concise. End with "**Confidence note:**" on sparse/uncertain areas."""


async def _search(query: str) -> str:
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(None, lambda: tavily_client.search(query, max_results=5))
    return "\n".join(
        f"- {r['title']}: {r['content']}" for r in response["results"]
    )


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def fetch_signal_data(company_name: str) -> dict:
    """Tavily-only: fetch all search data for signal detection."""
    results = await asyncio.gather(
        _search(f"{company_name} official website about"),
        _search(f"{company_name} tech stack technology API"),
        _search(f"{company_name} podcast audio content"),
        _search(f"{company_name} languages international multilingual"),
        _search(f"{company_name} voice audio TTS text to speech Twilio"),
        _search(f"{company_name} developer docs API SDK webhook"),
    )
    return {
        "website": results[0], "tech": results[1], "podcast": results[2],
        "language": results[3], "voice": results[4], "developer": results[5],
    }


async def synthesize_signals(company_name: str, data: dict) -> dict:
    """Claude-only: analyze fetched data and return structured signals."""
    search_data = "\n".join(
        f"--- {k.title()} ---\n{v}" for k, v in data.items()
    )
    prompt = SIGNAL_DETECTION_PROMPT.format(
        company_name=company_name, search_data=search_data,
    )
    text = await chat(
        prompt=prompt, max_tokens=768,
        system="Return only valid JSON, no markdown.",
    )
    try:
        result = json.loads(_strip_fences(text))
        # Ensure technical fields have defaults
        result.setdefault("existing_voice_stack", [])
        result.setdefault("is_api_first", False)
        result.setdefault("needs_realtime", False)
        result.setdefault("operates_at_scale", False)
        result.setdefault("language_count", 0)
        return result
    except json.JSONDecodeError:
        return {
            "company_name": company_name, "website": "",
            "signals_detected": [], "current_audio_tools": [],
            "evidence": [], "employee_count_estimate": "Unknown",
            "industry": "Unknown",
            "existing_voice_stack": [], "is_api_first": False,
            "needs_realtime": False, "operates_at_scale": False,
            "language_count": 0,
        }


async def fetch_company_data(company_name: str) -> dict:
    """Tavily-only: fetch search data for company research."""
    results = await asyncio.gather(
        _search(f"{company_name} AI startup"),
        _search(f"{company_name} product customers"),
        _search(f"{company_name} funding news"),
    )
    return {"ai_profile": results[0], "products": results[1], "funding": results[2]}


async def synthesize_company(company_name: str, data: dict, product_context: str) -> str:
    """Claude-only: synthesize company research into intel summary."""
    search_data = "\n".join(
        f"--- {k.replace('_', ' ').title()} ---\n{v}" for k, v in data.items()
    )
    prompt = SYNTHESIS_PROMPT.format(
        product_context=product_context, company_name=company_name,
        search_data=search_data,
    )
    return await chat(
        prompt=prompt, max_tokens=768,
        system="You are a senior industry analyst. Accuracy over comprehensiveness. Flag uncertainty.",
    )


# Legacy wrappers for backward compatibility
async def detect_signals(company_name: str) -> dict:
    data = await fetch_signal_data(company_name)
    return await synthesize_signals(company_name, data)


async def research_company(company_name: str, role: str, product_context: str = "") -> str:
    data = await fetch_company_data(company_name)
    return await synthesize_company(company_name, data, product_context)
