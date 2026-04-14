"""
HTML → clean text extraction, canonical URL resolution, and same-domain link extraction.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from autoquery.crawler.crawler_engine import normalize_url

# Tags stripped wholesale before text extraction
_REMOVE_TAGS = [
    "script", "style", "nav", "header", "footer", "aside",
]

# CSS selectors for noise elements (cookie banners, popups, etc.)
_REMOVE_SELECTORS = [
    "[class*=cookie]",
    ".banner",
    "[class*=popup]",
    "[id*=cookie]",
    "[id*=nav]",
    "[id*=footer]",
    "[id*=sidebar]",
]

_WHITESPACE_RE = re.compile(r"[ \t]+")
_NEWLINE_RE = re.compile(r"\n{3,}")


def extract_text(html: str) -> str:
    """Parse HTML and return clean prose text, stripping all navigation/chrome."""
    soup = BeautifulSoup(html, "lxml")

    for tag in _REMOVE_TAGS:
        for el in soup.find_all(tag):
            el.decompose()

    for selector in _REMOVE_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    text = soup.get_text(separator=" ", strip=True)

    # Collapse runs of spaces/tabs to a single space, then clean up newlines
    text = _WHITESPACE_RE.sub(" ", text)
    text = _NEWLINE_RE.sub("\n\n", text)
    return text.strip()


def extract_canonical_url(html: str, base_url: str) -> str:
    """Return the canonical URL from <link rel=canonical>, or base_url as fallback."""
    soup = BeautifulSoup(html, "lxml")
    tag = soup.find("link", rel="canonical")
    if tag and tag.get("href"):
        return str(tag["href"])
    return base_url


def extract_links(html: str, base_url: str) -> list[str]:
    """
    Return normalized, deduplicated links from the page restricted to the same domain.
    """
    soup = BeautifulSoup(html, "lxml")
    base_domain = urlparse(base_url).netloc.lower()
    if base_domain.startswith("www."):
        base_domain = base_domain[4:]
    seen: set[str] = set()
    links: list[str] = []

    for a in soup.find_all("a", href=True):
        href = str(a["href"]).strip()
        if not href or href.startswith(("#", "mailto:", "javascript:")):
            continue
        full = urljoin(base_url, href)
        parsed = urlparse(full)
        link_domain = parsed.netloc.lower()
        if link_domain.startswith("www."):
            link_domain = link_domain[4:]
        if link_domain != base_domain:
            continue
        normed = normalize_url(full)
        if normed not in seen:
            seen.add(normed)
            links.append(normed)

    return links
