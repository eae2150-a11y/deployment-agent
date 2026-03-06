"""Shared Anthropic client with retry logic for rate limits."""

import asyncio
import logging
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MAX_RETRIES = 4
BASE_DELAY = 3.0  # seconds


async def chat(
    *,
    prompt: str,
    system: str = "",
    max_tokens: int = 1024,
    model: str = "claude-sonnet-4-6",
) -> str:
    """Call Claude with exponential backoff on rate-limit errors."""
    messages = [{"role": "user", "content": prompt}]
    kwargs = dict(model=model, max_tokens=max_tokens, messages=messages)
    if system:
        kwargs["system"] = system

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.messages.create(**kwargs)
            return response.content[0].text
        except anthropic.RateLimitError:
            if attempt == MAX_RETRIES:
                raise
            delay = BASE_DELAY * (2 ** attempt)
            log.warning("Rate limited (attempt %d/%d), retrying in %.1fs", attempt + 1, MAX_RETRIES, delay)
            await asyncio.sleep(delay)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:  # overloaded
                if attempt == MAX_RETRIES:
                    raise
                delay = BASE_DELAY * (2 ** attempt)
                log.warning("API overloaded (attempt %d/%d), retrying in %.1fs", attempt + 1, MAX_RETRIES, delay)
                await asyncio.sleep(delay)
            else:
                raise
