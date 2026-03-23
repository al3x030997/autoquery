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

from autoquery.database.models import Agent, Agency, REVIEW_STATUS_PENDING, REVIEW_STATUS_EXTRACTION_FAILED
from autoquery.matching.genre_utils import load_genre_aliases
from autoquery.extractor.prompts import (
    EXTRACTION_SYSTEM_PROMPT,
    EXTRACTION_USER_PROMPT,
    MULTI_AGENT_ROSTER_SYSTEM_PROMPT,
    MULTI_AGENT_ROSTER_USER_PROMPT,
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
            data["genres_raw"] = list(data.get("genres", []))
            data["genres"] = self._canonicalize_genres(data.get("genres", []))
            closed_to_str = data.get("closed_to") or ""
            data["closed_to_raw"] = closed_to_str if isinstance(closed_to_str, str) else None
            data["closed_to"] = self._canonicalize_genres(
                [g.strip() for g in (closed_to_str if isinstance(closed_to_str, str) else "").split(",") if g.strip()]
            )

            # Grounding validation
            grounding_warnings = self._validate_grounding(data, clean_text)
            if grounding_warnings:
                logger.warning("Grounding issues for %s: %s", source_url, grounding_warnings)

            if data.get("_grounding_failed"):
                logger.warning("Skipping hallucinated agent '%s' from %s", data.get("name"), source_url)
                return self._upsert_agent(
                    db, source_url, data, quality_score, quality_action,
                    review_status=REVIEW_STATUS_EXTRACTION_FAILED,
                )

            # Wishlist validation
            wl_warnings = self._validate_wishlist(data, len(truncated.split()))
            if wl_warnings:
                logger.warning("Wishlist issues for %s: %s", source_url, wl_warnings)

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

    async def extract_multi(
        self,
        clean_text: str,
        source_url: str,
        quality_score: float,
        quality_action: str,
        db: Session,
    ) -> list[Agent]:
        """
        Two-pass multi-agent extraction.

        Pass 1: Roster extraction — get agent names + agency metadata (lightweight).
        Pass 2: Per-agent detail extraction — slice page text per agent, run
                 single-agent prompt on each section for full wishlist fidelity.
        """
        # Pass 1: roster (needs to see full page, use 8000 word limit)
        roster_text = self._truncate(clean_text, max_words=8000)

        try:
            roster = await self._call_ollama_roster(roster_text)
        except Exception as exc:
            logger.error("Ollama roster call failed for %s: %s", source_url, exc)
            return []

        # Upsert agency record if agency_info is present
        agency_info = roster.get("agency_info") or {}
        agency_obj = None
        if agency_info.get("name"):
            agency_obj = self._upsert_agency(db, source_url, agency_info)

        agents_roster = roster.get("agents", [])
        if not isinstance(agents_roster, list) or not agents_roster:
            logger.warning("Roster extraction returned no agents for %s", source_url)
            return []

        # Validate roster names against source text
        agent_names = [e.get("name", "") for e in agents_roster if isinstance(e, dict)]
        validated_roster = []
        for entry in agents_roster:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "").strip()
            if not name:
                continue
            # Check last name appears in source
            parts = name.split()
            last_name = parts[-1].lower() if parts else ""
            if last_name and last_name not in clean_text.lower():
                logger.warning("Roster name '%s' not found in source text — skipping", name)
                continue
            validated_roster.append(entry)

        if not validated_roster:
            logger.warning("No valid agent names in roster for %s", source_url)
            return []

        # Pass 2: per-agent detail extraction
        results: list[Agent] = []
        for i, entry in enumerate(validated_roster):
            agent_name = entry["name"]
            section_hint = entry.get("section_hint")

            section = self._extract_section(
                clean_text, agent_name, section_hint,
                all_names=[e["name"] for e in validated_roster],
            )

            try:
                agent_data = await self._call_ollama(section)
            except Exception as exc:
                logger.error("Ollama per-agent call failed for '%s' on %s: %s", agent_name, source_url, exc)
                continue

            is_valid, errors = self._validate(agent_data)
            if not is_valid:
                logger.warning(
                    "Multi-agent validation failed for '%s' on %s: %s", agent_name, source_url, errors
                )
                continue

            # Grounding validation against the agent's section
            grounding_warnings = self._validate_grounding(agent_data, section)
            if grounding_warnings:
                logger.warning("Grounding issues for '%s' on %s: %s", agent_name, source_url, grounding_warnings)
            if agent_data.get("_grounding_failed"):
                logger.warning("Skipping hallucinated agent '%s' from %s", agent_data.get("name"), source_url)
                continue

            # Build a unique profile_url per agent on the same page
            agent_name_slug = (agent_data.get("name") or "unknown").lower().replace(" ", "-")
            agent_url = f"{source_url}#agent-{agent_name_slug}"

            agent_data["genres_raw"] = list(agent_data.get("genres", []))
            agent_data["genres"] = self._canonicalize_genres(agent_data.get("genres", []))
            closed_to_str = agent_data.get("closed_to") or ""
            agent_data["closed_to_raw"] = closed_to_str if isinstance(closed_to_str, str) else None
            agent_data["closed_to"] = self._canonicalize_genres(
                [g.strip() for g in (closed_to_str if isinstance(closed_to_str, str) else "").split(",") if g.strip()]
            )
            # Carry agency name
            if agency_info.get("name") and not agent_data.get("agency"):
                agent_data["agency"] = agency_info["name"]
            # Carry agency response_time as default
            if agency_info.get("response_time") and not agent_data.get("response_time"):
                agent_data["response_time"] = agency_info["response_time"]

            # Wishlist validation
            wl_warnings = self._validate_wishlist(agent_data, len(section.split()))
            if wl_warnings:
                logger.warning("Wishlist issues for '%s' on %s: %s", agent_name, source_url, wl_warnings)

            agent = self._upsert_agent(
                db, agent_url, agent_data, quality_score, quality_action,
                review_status=REVIEW_STATUS_PENDING,
                agency_id=agency_obj.id if agency_obj else None,
            )
            results.append(agent)
            logger.info("Multi-extract (two-pass): %s from %s", agent_data.get("name"), source_url)

        return results

    async def _call_ollama_roster(self, clean_text: str) -> dict:
        """POST to Ollama for lightweight roster extraction (Pass 1)."""
        prompt = MULTI_AGENT_ROSTER_USER_PROMPT.format(clean_text=clean_text)

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "system": MULTI_AGENT_ROSTER_SYSTEM_PROMPT,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")

            start = raw.find("{")
            end = raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError(f"No JSON found in Ollama roster response: {raw[:200]}")
            return json.loads(raw[start:end])

    @staticmethod
    def _extract_section(
        text: str,
        agent_name: str,
        section_hint: str | None = None,
        all_names: list[str] | None = None,
    ) -> str:
        """
        Slice the page text to extract the section belonging to a specific agent.

        Finds the agent's name in the text, then takes text from that position
        until the next agent's name (or end of text). Falls back to section_hint
        as anchor if name isn't found verbatim.
        """
        text_lower = text.lower()
        name_lower = agent_name.lower()

        # Find start position — try full name, then last name
        start = text_lower.find(name_lower)
        if start == -1:
            # Try last name only
            parts = agent_name.split()
            if parts:
                last_name = parts[-1].lower()
                start = text_lower.find(last_name)

        if start == -1 and section_hint:
            # Fall back to section hint
            hint_lower = section_hint.lower().strip()
            if hint_lower:
                start = text_lower.find(hint_lower)

        if start == -1:
            # Can't locate — return full text as fallback
            return text

        # Find end position — next agent's name or end of text
        end = len(text)
        if all_names:
            for other_name in all_names:
                if other_name.lower() == name_lower:
                    continue
                other_pos = text_lower.find(other_name.lower(), start + len(agent_name))
                if other_pos != -1 and other_pos < end:
                    end = other_pos

        return text[start:end].strip()

    @staticmethod
    def _upsert_agency(db: Session, source_url: str, agency_info: dict) -> Agency:
        """Insert or update Agency by name."""
        from urllib.parse import urlparse

        name = agency_info["name"].strip()
        domain = urlparse(source_url).netloc.lower()

        existing = db.query(Agency).filter_by(name=name).first()
        if not existing:
            existing = db.query(Agency).filter_by(domain=domain).first()

        fields = {
            "name": name,
            "domain": domain,
            "country": agency_info.get("country"),
            "exclusive_query": bool(agency_info.get("exclusive_query", False)),
            "submission_url": agency_info.get("submission_url"),
            "response_time": agency_info.get("response_time"),
        }

        if existing:
            for k, v in fields.items():
                if v is not None:
                    setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            agency = Agency(**fields)
            db.add(agency)
            db.commit()
            db.refresh(agency)
            return agency

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
    def _validate_wishlist(data: dict, section_word_count: int) -> list[str]:
        """Warn if wishlist seems truncated relative to source text."""
        warnings: list[str] = []
        wishlist = data.get("wishlist_raw") or ""
        if section_word_count > 100 and len(wishlist.split()) < 20:
            warnings.append(
                f"wishlist_raw suspiciously short ({len(wishlist.split())} words) "
                f"for {section_word_count}-word section"
            )
        return warnings

    @staticmethod
    def _validate_grounding(data: dict, source_text: str) -> list[str]:
        """Check that key extracted fields appear in the source text."""
        warnings: list[str] = []
        text_lower = source_text.lower()

        # 1. Name must appear in source text (check last name at minimum)
        name = (data.get("name") or "").strip()
        if name:
            parts = name.split()
            last_name = parts[-1].lower() if parts else ""
            if last_name and last_name not in text_lower:
                warnings.append(f"name '{name}' not found in source text")
                data["_grounding_failed"] = True

        # 2. Email must appear in source text (if extracted)
        email = data.get("email")
        if isinstance(email, str) and email.strip().lower() == "null":
            data["email"] = None
            email = None
        if email and email.lower() not in text_lower:
            warnings.append(f"email '{email}' not found in source text — removing")
            data["email"] = None

        # 3. Wishlist should have substantial overlap with source text
        wishlist = data.get("wishlist_raw") or ""
        if wishlist and len(wishlist.split()) > 10:
            wl_words = set(
                w.lower().strip(".,;:!?\"'()")
                for w in wishlist.split()
                if len(w) > 3
            )
            if wl_words:
                overlap = sum(1 for w in wl_words if w in text_lower)
                overlap_ratio = overlap / len(wl_words)
                if overlap_ratio < 0.3:
                    warnings.append(
                        f"wishlist_raw has low source overlap ({overlap_ratio:.0%}) — possible hallucination"
                    )

        return warnings

    @staticmethod
    def _sanitize_llm_data(data: dict) -> None:
        """Coerce LLM string artifacts to proper Python types in-place.

        LLMs sometimes return the literal string "null", "true", "false"
        instead of JSON null/true/false.  Fix these before DB insertion.
        """
        # is_open: coerce to bool or None
        is_open = data.get("is_open")
        if isinstance(is_open, str):
            low = is_open.strip().lower()
            data["is_open"] = {"true": True, "false": False}.get(low)

        # Text fields: convert literal "null" to None
        for key in ("wishlist_raw", "bio_raw", "hard_nos_raw", "email",
                     "closed_to_raw", "response_time", "agency", "country"):
            val = data.get(key)
            if isinstance(val, str) and val.strip().lower() == "null":
                data[key] = None

    @staticmethod
    def _upsert_agent(
        db: Session,
        source_url: str,
        data: dict,
        quality_score: float,
        quality_action: str,
        review_status: str,
        agency_id: int | None = None,
    ) -> Agent:
        """Insert or update Agent by profile_url."""
        ProfileExtractor._sanitize_llm_data(data)

        existing = db.query(Agent).filter_by(profile_url=source_url).first()

        name = data.get("name", "").strip() if data.get("name") else ""

        fields = {
            "name": name or "(extraction failed)",
            "agency": data.get("agency"),
            "agency_id": agency_id,
            "genres": data.get("genres") or [],
            "genres_raw": data.get("genres_raw") or [],
            "keywords": data.get("keywords") or [],
            "audience": data.get("audience") or [],
            "hard_nos_keywords": data.get("hard_nos_keywords") or [],
            "submission_req": data.get("submission_req"),
            "is_open": data.get("is_open"),
            "wishlist_raw": data.get("wishlist_raw"),
            "bio_raw": data.get("bio_raw"),
            "hard_nos_raw": data.get("hard_nos_raw"),
            "email": data.get("email"),
            "closed_to_raw": data.get("closed_to_raw"),
            "closed_to": data.get("closed_to") or [],
            "response_time": data.get("response_time"),
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
