"""ElevenLabs Product Matching Agent - maps company signals to specific EL products with technical precision."""

import json

from backend.llm import chat

SYSTEM_PROMPT = """You are an ElevenLabs solutions architect. You match prospects to products with technical precision.

ElevenLabs Products:
1. Text to Speech API - 32 langs, 3000+ voices, 75ms latency. REST batch or WebSocket streaming. Best: notifications, content, e-learning, accessibility, comms at scale.
2. Voice Cloning - Clone voice from 1min audio (Instant) or 30min (Professional). Best: media, podcasters, gaming, brand voice, audiobooks.
3. Dubbing API - Translate+re-voice into 29 langs preserving speaker voice. End-to-end pipeline. Best: YouTube, streaming, training, marketing videos.
4. Conversational AI (ElevenAgents) - Voice agents for phone/web. Ultra-low latency. Twilio/SIP/PSTN native. Best: IVR replacement, support deflection, sales, scheduling.
5. Reader App - iOS/Android reads content aloud. White-label available. Best: publishers, newsletters, accessibility.

Models:
- Eleven Multilingual v2: best quality, 29 langs. Use for content/dubbing.
- Eleven Turbo v2.5: lowest latency (~75ms). Use for real-time conversational agents.
- Eleven English v2: highest quality English-only.
- Scribe v2: batch transcription, subtitling, captioning.
- Scribe v2 Realtime: ultra-low latency live STT with VAD commit. Use for voice agents needing live transcription.

Integration Patterns:
- REST API (batch TTS): simplest, async content generation
- Streaming API: low latency real-time TTS
- WebSocket (Scribe v2 Realtime): live transcription
- ElevenAgents platform: no-code agent builder, native Twilio/phone integration
- React SDK (@elevenlabs/react): client-side streaming with single-use token auth

Architecture Patterns:
- Basic Cascaded: STT -> LLM -> TTS (simple, higher latency)
- Advanced Cascaded: Scribe v2 Realtime STT + LLM reasoning + EL TTS with Expressive Mode (best for tool use/guardrails)
- Sequential Fused: e.g. OpenAI Realtime (single model, lower latency, less control)

Known Integrations: Twilio (native phone/IVR), standard webhooks for agent handoffs.

Competitors by category:
- TTS: Murf, Play.ht, WellSaid, Azure TTS, Lovo.ai, Amazon Polly, Google TTS
- Voice Cloning: Resemble.ai
- Dubbing: no direct competitor at same quality
- Conversational AI: Deepgram, Bland.ai, Vapi, OpenAI Realtime
- Reader: Speechify

Migration complexity:
- low: API-first company, no existing voice stack, or stack is easily composable (e.g. Twilio+Polly = easy swap)
- medium: Has existing voice tooling not deeply embedded, or has some real-time requirements
- high: Custom-built voice stack, fused model deployed, or heavily embedded competitor

Return ONLY valid JSON."""

MATCHING_PROMPT = """Company: {company_name} | Industry: {industry}
Signals: {signals} | Audio tools: {current_tools}
Existing voice stack: {existing_voice_stack}
Is API-first: {is_api_first} | Needs realtime: {needs_realtime}
Operates at scale: {operates_at_scale} | Language count: {language_count}
Evidence: {evidence}
Employees: {employee_count} | Notes: {user_notes}

Return JSON with technically precise product matching:
{{
  "primary_product": "product name",
  "primary_reason": "1-2 sentences with evidence",
  "integration_pattern": "specific pattern e.g. 'Advanced Cascaded — Scribe v2 Realtime STT + LLM reasoning + EL TTS Expressive Mode'",
  "why_not_fused": "if ConvAI: why cascaded beats fused for this use case. Otherwise empty string.",
  "existing_stack_conflict": "how EL relates to their current stack — replacement, complement, or addition. Mention specific vendors.",
  "migration_complexity": "low/medium/high",
  "migration_reason": "one sentence explaining the rating",
  "recommended_model": "specific EL model name (Multilingual v2, Turbo v2.5, English v2, etc.)",
  "recommended_architecture": "Basic Cascaded / Advanced Cascaded / REST batch / Streaming API / ElevenAgents",
  "scribe_v2_realtime_relevant": true/false,
  "secondary_product": "product name",
  "secondary_reason": "1-2 sentences",
  "fit_score": 0-100,
  "fit_tier": "Hot(70+)/Warm(45-69)/Cold(<45)",
  "fit_rationale": "2-3 sentences",
  "likely_competitors": ["competitors they are likely evaluating"],
  "competitive_risk": "primary competitive threat (specific product, not company)",
  "competitive_angle": "what to lead with against that competitor — be specific",
  "key_objection": "most likely objection",
  "winning_angle": "strongest hook for this specific company"
}}"""


def _strip_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
    return text.strip()


async def match_products(
    company_name: str,
    signals: dict,
    user_notes: str = "",
) -> dict:
    """Take company signals and map them to the best ElevenLabs product fit with technical detail."""
    prompt = MATCHING_PROMPT.format(
        company_name=company_name,
        industry=signals.get("industry", "Unknown"),
        signals=", ".join(signals.get("signals_detected", [])),
        current_tools=", ".join(signals.get("current_audio_tools", [])) or "None detected",
        existing_voice_stack=", ".join(signals.get("existing_voice_stack", [])) or "None detected",
        is_api_first=signals.get("is_api_first", False),
        needs_realtime=signals.get("needs_realtime", False),
        operates_at_scale=signals.get("operates_at_scale", False),
        language_count=signals.get("language_count", 0),
        evidence="\n".join(f"- {e}" for e in signals.get("evidence", [])) or "No direct evidence",
        employee_count=signals.get("employee_count_estimate", "Unknown"),
        user_notes=user_notes or "None provided",
    )

    text = await chat(prompt=prompt, max_tokens=768, system=SYSTEM_PROMPT)

    try:
        result = json.loads(_strip_fences(text))
        # Ensure technical fields have defaults
        result.setdefault("integration_pattern", "")
        result.setdefault("why_not_fused", "")
        result.setdefault("existing_stack_conflict", "")
        result.setdefault("migration_complexity", "medium")
        result.setdefault("migration_reason", "")
        result.setdefault("recommended_model", "Eleven Multilingual v2")
        result.setdefault("recommended_architecture", "REST batch")
        result.setdefault("scribe_v2_realtime_relevant", False)
        result.setdefault("competitive_risk", "")
        result.setdefault("competitive_angle", "")
        return result
    except json.JSONDecodeError:
        return {
            "primary_product": "Text to Speech API",
            "primary_reason": "Default — signal detection was inconclusive",
            "integration_pattern": "REST API (batch TTS)",
            "why_not_fused": "",
            "existing_stack_conflict": "Unknown — manual review needed",
            "migration_complexity": "medium",
            "migration_reason": "Insufficient data to assess",
            "recommended_model": "Eleven Multilingual v2",
            "recommended_architecture": "REST batch",
            "scribe_v2_realtime_relevant": False,
            "secondary_product": "Conversational AI",
            "secondary_reason": "Broad applicability for enterprise prospects",
            "fit_score": 30, "fit_tier": "Cold",
            "fit_rationale": "Unable to parse results. Manual review recommended.",
            "likely_competitors": [],
            "competitive_risk": "Unknown",
            "competitive_angle": "Unknown",
            "key_objection": "Unknown",
            "winning_angle": "Unknown",
        }
