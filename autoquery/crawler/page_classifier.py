"""
Ollama-based page type classifier: INDEX | CONTENT | UNKNOWN.
"""
from __future__ import annotations

import json
import os
from enum import Enum

import httpx

from autoquery.crawler.content_extractor import extract_text

_PROMPT_TEMPLATE = """\
You are classifying a literary agency webpage.
Respond with JSON only: {{"page_type": "INDEX" | "CONTENT" | "UNKNOWN"}}
INDEX = page listing multiple agents (e.g. /our-agents, /team)
CONTENT = page for a single agent with their bio/wishlist
URL: {url}
Page text (first 2000 chars):
{text}
"""


class PageType(str, Enum):
    INDEX = "INDEX"
    CONTENT = "CONTENT"
    UNKNOWN = "UNKNOWN"


async def classify_page(html: str, url: str, ollama_url: str) -> PageType:
    """
    Classify a page as INDEX, CONTENT, or UNKNOWN using Ollama.
    Returns UNKNOWN on any network or parse error — never raises.
    """
    model = os.environ.get("EMBEDDING_MODEL", "llama3")
    text = extract_text(html)[:2000]
    prompt = _PROMPT_TEMPLATE.format(url=url, text=text)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            # Extract JSON from the response (may have surrounding text)
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                return PageType.UNKNOWN
            data = json.loads(raw[start:end])
            page_type_str = data.get("page_type", "UNKNOWN").upper()
            return PageType(page_type_str) if page_type_str in PageType.__members__ else PageType.UNKNOWN
    except Exception:
        return PageType.UNKNOWN
