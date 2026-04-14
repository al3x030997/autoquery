"""
Page type classifier: INDEX | CONTENT | MULTI_AGENT | UNKNOWN.

Supports two backends:
- claude (default): uses Anthropic API via anthropic SDK
- ollama: uses local Ollama instance
"""
from __future__ import annotations

import json
import logging
import os
from enum import Enum

import anthropic
import httpx

from autoquery.crawler.content_extractor import extract_text

logger = logging.getLogger(__name__)

_PROMPT_TEMPLATE = """\
You are classifying a literary agency webpage.
Respond with JSON only: {{"page_type": "INDEX" | "CONTENT" | "MULTI_AGENT" | "CLIENT_BIO" | "UNKNOWN"}}
INDEX = page listing multiple agents with links to individual pages (e.g. /our-agents, /team)
CONTENT = page for a single LITERARY AGENT with their bio, wishlist, or submission preferences. The person IS an agent who represents authors.
MULTI_AGENT = page with detailed info (bios, wishlists, submission preferences) about MULTIPLE agents on one page (e.g. /about with multiple bios, /submissions with per-agent wishlists)
CLIENT_BIO = page for an author, illustrator, or artist who is REPRESENTED BY an agent at the agency. Signals: "Represented by [name]", "Agent: [name]", describes the person as "author", "writer", "illustrator", "artist". This is NOT an agent profile.
UNKNOWN = none of the above
URL: {url}
Page text (first 2000 chars):
{text}
"""


class PageType(str, Enum):
    INDEX = "INDEX"
    CONTENT = "CONTENT"
    MULTI_AGENT = "MULTI_AGENT"
    UNKNOWN = "UNKNOWN"


# Lazy-initialised Claude client (module-level singleton)
_claude_client: anthropic.AsyncAnthropic | None = None


def _get_claude_client() -> anthropic.AsyncAnthropic:
    global _claude_client
    if _claude_client is None:
        _claude_client = anthropic.AsyncAnthropic()
    return _claude_client


def _parse_page_type(raw: str) -> PageType:
    """Extract PageType from a JSON string, tolerating surrounding text."""
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        return PageType.UNKNOWN
    data = json.loads(raw[start:end])
    page_type_str = data.get("page_type", "UNKNOWN").upper()
    if page_type_str == "CLIENT_BIO":
        return PageType.UNKNOWN
    return PageType(page_type_str) if page_type_str in PageType.__members__ else PageType.UNKNOWN


async def _classify_claude(text: str, url: str) -> PageType:
    """Classify using the Anthropic API."""
    model = os.environ.get("CLASSIFIER_CLAUDE_MODEL", "claude-haiku-4-5-20251001")
    prompt = _PROMPT_TEMPLATE.format(url=url, text=text)
    client = _get_claude_client()
    resp = await client.messages.create(
        model=model,
        max_tokens=64,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text
    return _parse_page_type(raw)


async def _classify_ollama(text: str, url: str, ollama_url: str) -> PageType:
    """Classify using a local Ollama instance."""
    model = os.environ.get("CLASSIFIER_MODEL", "llama3.2:3b")
    prompt = _PROMPT_TEMPLATE.format(url=url, text=text)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ollama_url}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        resp.raise_for_status()
        raw = resp.json().get("response", "")
        return _parse_page_type(raw)


async def classify_page(
    html: str, url: str, ollama_url: str, *, classifier_backend: str | None = None
) -> PageType:
    """
    Classify a page as INDEX, CONTENT, MULTI_AGENT, or UNKNOWN.
    Returns UNKNOWN on any failure — never raises.
    """
    backend = classifier_backend or os.environ.get("CLASSIFIER_BACKEND", "claude")
    text = extract_text(html)[:2000]

    try:
        if backend == "claude":
            return await _classify_claude(text, url)
        else:
            return await _classify_ollama(text, url, ollama_url)
    except Exception:
        logger.exception("Page classification failed (backend=%s, url=%s)", backend, url)
        return PageType.UNKNOWN
