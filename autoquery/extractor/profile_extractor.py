"""
Ollama-based profile extraction: clean text → structured Agent fields.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from autoquery.database.models import Agent, REVIEW_STATUS_PENDING, REVIEW_STATUS_EXTRACTION_FAILED
from autoquery.matching.genre_utils import load_genre_aliases
from autoquery.extractor.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    PROMPT_VERSION,
)

logger = logging.getLogger(__name__)

_GENRE_CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "genre_aliases.yaml"


class ProfileExtractor:
    """Extract structured agent profiles from clean text using Ollama."""

    def __init__(
        self,
        ollama_url: str | None = None,
        model: str | None = None,
        genre_config_path: str | Path | None = None,
    ):
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://ollama:11434")
        self.model = model or os.environ.get("EXTRACTOR_MODEL", "llama3.1:8b")
        self._genre_aliases = load_genre_aliases(genre_config_path or _GENRE_CONFIG_PATH)

    async def extract(
        self,
        clean_text: str,
        source_url: str,
        quality_score: float,
        quality_action: str,
        db: Session,
    ) -> Agent | None:
        """
        Extract agent profile from clean text and upsert to DB.

        Returns the Agent object, or None on total failure.
        """
        truncated = self._truncate(clean_text)

        try:
            data = await self._call_ollama(truncated)
        except Exception as exc:
            logger.error("Ollama call failed for %s: %s", source_url, exc)
            return self._upsert_agent(
                db, source_url, {}, quality_score, quality_action,
                review_status=REVIEW_STATUS_EXTRACTION_FAILED,
            )

        is_valid, errors = self._validate(data)

        if is_valid:
            data["genres"] = self._canonicalize_genres(data.get("genres", []))
            agent = self._upsert_agent(
                db, source_url, data, quality_score, quality_action,
                review_status=REVIEW_STATUS_PENDING,
            )
            logger.info("Extracted profile for %s: %s", source_url, data.get("name"))
            return agent
        else:
            logger.warning(
                "Extraction validation failed for %s: %s", source_url, errors
            )
            return self._upsert_agent(
                db, source_url, data, quality_score, quality_action,
                review_status=REVIEW_STATUS_EXTRACTION_FAILED,
            )

    async def _call_ollama(self, clean_text: str) -> dict:
        """POST to Ollama /api/generate with JSON format enforced."""
        prompt = EXTRACTION_USER_PROMPT.format(clean_text=clean_text)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "system": EXTRACTION_SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")

            # Parse JSON from response
            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError(f"No JSON found in Ollama response: {raw[:200]}")
            return json.loads(raw[start:end])

    def _validate(self, data: dict) -> tuple[bool, list[str]]:
        """Check required fields. Returns (is_valid, error_list)."""
        errors: list[str] = []

        name = data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            errors.append("missing or empty 'name'")

        genres = data.get("genres", [])
        if not isinstance(genres, list) or len(genres) < 1:
            errors.append("need at least 1 genre")

        keywords = data.get("keywords", [])
        if not isinstance(keywords, list) or len(keywords) < 3:
            errors.append("need at least 3 keywords")

        return (len(errors) == 0, errors)

    def _canonicalize_genres(self, genres: list[str]) -> list[str]:
        """Map genres through alias lookup, deduplicate."""
        canonical: list[str] = []
        seen: set[str] = set()
        for g in genres:
            if not isinstance(g, str):
                continue
            key = g.lower().strip()
            mapped = self._genre_aliases.get(key, key)
            if mapped not in seen:
                seen.add(mapped)
                canonical.append(mapped)
        return canonical

    def _truncate(self, text: str, max_words: int = 4000) -> str:
        """Truncate text to max_words."""
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])

    @staticmethod
    def _upsert_agent(
        db: Session,
        source_url: str,
        data: dict,
        quality_score: float,
        quality_action: str,
        review_status: str,
    ) -> Agent:
        """Insert or update Agent by profile_url."""
        existing = db.query(Agent).filter_by(profile_url=source_url).first()

        name = data.get("name", "").strip() if data.get("name") else ""

        fields = {
            "name": name or "(extraction failed)",
            "agency": data.get("agency"),
            "genres": data.get("genres") or [],
            "keywords": data.get("keywords") or [],
            "audience": data.get("audience") or [],
            "hard_nos_keywords": data.get("hard_nos_keywords") or [],
            "submission_req": data.get("submission_req"),
            "is_open": data.get("is_open"),
            "wishlist_raw": data.get("wishlist_raw"),
            "bio_raw": data.get("bio_raw"),
            "hard_nos_raw": data.get("hard_nos_raw"),
            "email": data.get("email"),
            "quality_score": quality_score,
            "quality_action": quality_action,
            "review_status": review_status,
            "last_crawled_at": datetime.now(timezone.utc),
        }

        if existing:
            for k, v in fields.items():
                setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            agent = Agent(profile_url=source_url, **fields)
            db.add(agent)
            db.commit()
            db.refresh(agent)
            return agent
