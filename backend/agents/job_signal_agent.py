"""Job Signal Agent - detects hiring signals that indicate buying intent for ElevenLabs products."""

import asyncio
import json
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from backend.llm import chat

load_dotenv()

tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

JOB_SIGNAL_PROMPT = """Analyze job search results for "{company_name}" and extract hiring signals relevant to ElevenLabs voice AI.

HIGH INTENT titles -> product:
- Localization/Dubbing roles -> Dubbing API
- Voice UX/Researcher -> TTS API / Conversational AI
- Audio Engineer/Producer -> Voice Cloning / TTS API
- L10n/i18n Engineer -> Dubbing API
- Conversational AI/Voice Agent -> Conversational AI
- Content Operations -> TTS API / Reader App
- Podcast Producer -> Voice Cloning
- Contact Center/IVR -> Conversational AI

MEDIUM: ML/AI Engineer, Content Strategist, CX roles
LOW: Generic software/marketing roles (exclude unless voice/audio context)

For each job also determine:
- seniority: "IC" (individual contributor engineer) or "manager" (lead/manager/director/VP)
  IC = building something new (easier sale). Manager = scaling something existing.
- greenfield_or_migration: "greenfield" if building from scratch (e.g. "Voice Platform Engineer", no mention of replacing), "migration" if replacing/migrating (e.g. "Twilio Migration Engineer"), "unknown" if unclear
- implication: one sentence on what this hire means for ElevenLabs sales opportunity

{search_data}

Return ONLY valid JSON:
{{
  "jobs_found": [
    {{
      "title": "job title",
      "product_signal": "ElevenLabs product",
      "intent_level": "high/medium/low",
      "greenfield_or_migration": "greenfield/migration/unknown",
      "seniority": "IC/manager",
      "implication": "what this hire means for EL sales",
      "source_url": "",
      "posted_date": ""
    }}
  ],
  "top_signal": "strongest hiring signal summary",
  "intent_score": 0-100
}}

Score: 80-100 multiple high-intent roles, 60-79 one high or several medium, 30-59 medium only, 1-29 low only, 0 none found."""


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


async def fetch_job_data(company_name: str) -> dict:
    """Tavily-only: fetch job posting search data."""
    results = await asyncio.gather(
        _search(f"{company_name} jobs voice audio localization"),
        _search(f"{company_name} hiring dubbing TTS speech"),
        _search(f"{company_name} careers engineer linguist"),
    )
    return {"voice_jobs": results[0], "dubbing_jobs": results[1], "career_jobs": results[2]}


async def synthesize_job_signals(company_name: str, data: dict) -> dict:
    """Claude-only: analyze job data and return structured signals."""
    search_data = "\n".join(f"--- {k.replace('_', ' ').title()} ---\n{v}" for k, v in data.items())
    prompt = JOB_SIGNAL_PROMPT.format(company_name=company_name, search_data=search_data)
    text = await chat(
        prompt=prompt, max_tokens=768,
        system="Return only valid JSON, no markdown.",
    )
    try:
        result = json.loads(_strip_fences(text))
        # Ensure new fields have defaults on each job
        for job in result.get("jobs_found", []):
            job.setdefault("greenfield_or_migration", "unknown")
            job.setdefault("seniority", "IC")
            job.setdefault("implication", "")
        return result
    except json.JSONDecodeError:
        return {"jobs_found": [], "top_signal": "Unable to parse", "intent_score": 0}


async def detect_job_signals(company_name: str) -> dict:
    data = await fetch_job_data(company_name)
    return await synthesize_job_signals(company_name, data)
