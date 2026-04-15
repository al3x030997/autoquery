"""Profile extraction: clean text → Note-Taker output → structured Agent.

Backends:
  - "claude" (default): Anthropic Messages API
  - "ollama": local Ollama /api/generate

L1 prompt v2.0 (Note-Taker) emits plain text; we parse it via
``autoquery.extractor.note_parser`` and persist the structured form
(``profile_notes`` JSONB). Existing flat columns (genres, audience,
hard_nos_keywords, keywords, wishlist_raw) are filled best-effort as a
compatibility projection until the matcher / embeddings / review UI are
rewritten to consume sections natively.
"""
from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone

import anthropic
import httpx
from sqlalchemy import func
from sqlalchemy.orm import Session

from autoquery.database.models import Agent, Agency, REVIEW_STATUS_PENDING
from autoquery.extractor import note_parser
from autoquery.extractor.prompts import (
    NOTE_TAKER_SYSTEM_PROMPT,
    MULTI_AGENT_ROSTER_SYSTEM_PROMPT,
    MULTI_AGENT_ROSTER_USER_PROMPT,
    PROMPT_VERSION,
)

logger = logging.getLogger(__name__)


class ProfileExtractor:
    """Extract structured agent profiles using Claude or Ollama."""

    def __init__(
        self,
        ollama_url: str | None = None,
        model: str | None = None,
        anthropic_api_key: str | None = None,
        extractor_backend: str | None = None,
    ):
        self.ollama_url = ollama_url or os.environ.get("OLLAMA_URL", "http://ollama:11434")
        self.model = model or os.environ.get("EXTRACTOR_MODEL", "llama3.1:8b")
        self._backend = extractor_backend or os.environ.get("EXTRACTOR_BACKEND", "claude")

        if self._backend == "claude":
            api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
            self._claude = anthropic.AsyncAnthropic(api_key=api_key)
            self._claude_model = os.environ.get(
                "EXTRACTOR_CLAUDE_MODEL", "claude-haiku-4-5-20251001"
            )

    @staticmethod
    def _is_likely_client_bio(clean_text: str) -> bool:
        """Return True if the text describes an author/illustrator client, not an agent."""
        has_client_signal = bool(
            re.search(
                r"(?i)\b(?:represented by|(?:her|his|their)\s+agent\b|agent:\s*[A-Z])",
                clean_text,
            )
        )
        if not has_client_signal:
            return False
        has_agent_signal = bool(
            re.search(
                r"(?i)\b(?:query me|submission|wishlist|mswl|looking for|seeking)\b",
                clean_text,
            )
        )
        return not has_agent_signal

    async def extract(
        self,
        clean_text: str,
        source_url: str,
        quality_score: float,
        quality_action: str,
        db: Session,
    ) -> Agent | None:
        """Extract agent profile from clean text and upsert to DB."""
        if self._is_likely_client_bio(clean_text):
            logger.info("Skipping likely client bio page: %s", source_url)
            return None

        truncated = self._truncate(clean_text)

        try:
            raw_text = await self._call_llm(truncated)
        except Exception as exc:
            logger.error("LLM call failed for %s: %s", source_url, exc)
            return None

        parsed = note_parser.parse(raw_text)
        if not self._validate_notes(parsed):
            logger.warning("Note-Taker output missing required identity for %s", source_url)
            return None

        if not self._grounded(parsed, clean_text):
            logger.warning("Skipping ungrounded extraction for %s", source_url)
            return None

        fields = self._project_to_columns(parsed, raw_text)
        agent = self._upsert_agent(
            db, source_url, fields, quality_score, quality_action,
            review_status=REVIEW_STATUS_PENDING,
        )
        logger.info("Extracted profile for %s: %s", source_url, fields["name"])
        return agent

    async def extract_multi(
        self,
        clean_text: str,
        source_url: str,
        quality_score: float,
        quality_action: str,
        db: Session,
    ) -> list[Agent]:
        """Two-pass multi-agent extraction (roster JSON, then per-agent Note-Taker)."""
        roster_text = self._truncate(clean_text, max_words=8000)

        try:
            roster = await self._call_llm_roster(roster_text)
        except Exception as exc:
            logger.error("LLM roster call failed for %s: %s", source_url, exc)
            return []

        agency_info = roster.get("agency_info") or {}
        agency_obj = self._upsert_agency(db, source_url, agency_info) if agency_info.get("name") else None

        agents_roster = roster.get("agents", [])
        if not isinstance(agents_roster, list) or not agents_roster:
            logger.warning("Roster extraction returned no agents for %s", source_url)
            return []

        validated: list[dict] = []
        for entry in agents_roster:
            if not isinstance(entry, dict):
                continue
            name = (entry.get("name") or "").strip()
            if not name:
                continue
            last_name = name.split()[-1].lower()
            if last_name and last_name not in clean_text.lower():
                logger.warning("Roster name '%s' not found in source — skipping", name)
                continue
            validated.append(entry)
        if not validated:
            return []

        results: list[Agent] = []
        for entry in validated:
            agent_name = entry["name"]
            section_hint = entry.get("section_hint")
            section = self._extract_section(
                clean_text, agent_name, section_hint,
                all_names=[e["name"] for e in validated],
            )

            try:
                raw_text = await self._call_llm(section)
            except Exception as exc:
                logger.error("LLM per-agent call failed for '%s' on %s: %s", agent_name, source_url, exc)
                continue

            parsed = note_parser.parse(raw_text)
            if not self._validate_notes(parsed):
                logger.warning("Note-Taker output invalid for '%s' on %s", agent_name, source_url)
                continue
            if not self._grounded(parsed, section):
                logger.warning("Skipping ungrounded per-agent extraction for '%s' on %s", agent_name, source_url)
                continue

            fields = self._project_to_columns(parsed, raw_text)
            if agency_info.get("name") and not fields.get("agency"):
                fields["agency"] = agency_info["name"]
            if agency_info.get("response_time") and not fields.get("response_time"):
                fields["response_time"] = agency_info["response_time"]

            slug = (fields.get("name") or "unknown").lower().replace(" ", "-")
            agent_url = f"{source_url}#agent-{slug}"

            agent = self._upsert_agent(
                db, agent_url, fields, quality_score, quality_action,
                review_status=REVIEW_STATUS_PENDING,
                agency_id=agency_obj.id if agency_obj else None,
            )
            results.append(agent)
            logger.info("Multi-extract: %s from %s", fields.get("name"), source_url)
        return results

    # ------------------------------------------------------------------
    # Backend routing
    # ------------------------------------------------------------------

    async def _call_llm(self, clean_text: str) -> str:
        if self._backend == "claude":
            return await self._call_claude(clean_text)
        return await self._call_ollama(clean_text)

    async def _call_llm_roster(self, clean_text: str) -> dict:
        if self._backend == "claude":
            return await self._call_claude_roster(clean_text)
        return await self._call_ollama_roster(clean_text)

    async def _call_claude(self, clean_text: str) -> str:
        response = await self._claude.messages.create(
            model=self._claude_model,
            max_tokens=4096,
            system=NOTE_TAKER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": clean_text}],
        )
        return response.content[0].text

    async def _call_ollama(self, clean_text: str) -> str:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "system": NOTE_TAKER_SYSTEM_PROMPT,
                    "prompt": clean_text,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def _call_claude_roster(self, clean_text: str) -> dict:
        import json
        prompt = MULTI_AGENT_ROSTER_USER_PROMPT.format(clean_text=clean_text)
        response = await self._claude.messages.create(
            model=self._claude_model,
            max_tokens=4096,
            system=MULTI_AGENT_ROSTER_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text
        start, end = raw.find("{"), raw.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError(f"No JSON in roster response: {raw[:200]}")
        return json.loads(raw[start:end])

    async def _call_ollama_roster(self, clean_text: str) -> dict:
        import json
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
            start, end = raw.find("{"), raw.rfind("}") + 1
            if start == -1 or end == 0:
                raise ValueError(f"No JSON in roster response: {raw[:200]}")
            return json.loads(raw[start:end])

    # ------------------------------------------------------------------
    # Validation & projection
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_notes(parsed: dict) -> bool:
        name = (parsed.get("identity") or {}).get("name")
        return bool(name and isinstance(name, str) and name.strip())

    @staticmethod
    def _grounded(parsed: dict, source_text: str) -> bool:
        """Reject hallucinated names/emails."""
        text_lower = source_text.lower()
        ident = parsed.get("identity") or {}
        name = (ident.get("name") or "").strip()
        if name:
            last = name.split()[-1].lower()
            if last and last not in text_lower:
                logger.warning("Name '%s' not found in source text", name)
                return False
        email = ident.get("email")
        if email and email.lower() not in text_lower:
            logger.warning("Email '%s' not found in source text — clearing", email)
            ident["email"] = None
        return True

    @staticmethod
    def _project_to_columns(parsed: dict, raw_text: str) -> dict:
        """Best-effort projection from sections to legacy flat columns."""
        ident = parsed.get("identity") or {}
        sections = parsed.get("preference_sections") or []
        hard_nos = parsed.get("hard_nos") or {}
        themes = parsed.get("cross_cutting_themes") or []

        def _flatten_unique(values):
            seen, out = set(), []
            for v in values:
                if v and v not in seen:
                    seen.add(v)
                    out.append(v)
            return out

        genres_raw = _flatten_unique(g for s in sections for g in s.get("genres", []))
        audiences = _flatten_unique(a for s in sections for a in s.get("audience", []))
        hard_nos_flat = _flatten_unique(
            list(hard_nos.get("content", []))
            + list(hard_nos.get("format", []))
            + list(hard_nos.get("trope", []))
            + list(hard_nos.get("category", []))
        )
        keywords = _flatten_unique(
            list(themes)
            + [w for s in sections for w in s.get("wants", [])][:20]
        )

        availability = ident.get("availability")
        is_open = None
        if availability:
            up = availability.upper()
            if up == "OPEN":
                is_open = True
            elif up == "CLOSED":
                is_open = False

        return {
            "name": (ident.get("name") or "").strip() or "(extraction failed)",
            "agency": ident.get("organization"),
            "email": ident.get("email"),
            "is_open": is_open,
            "genres": [],          # canonicalized form left empty until L2 runtime is wired
            "genres_raw": genres_raw,
            "audience": audiences,
            "hard_nos_keywords": hard_nos_flat,
            "keywords": keywords,
            "submission_req": {"blocks": parsed.get("submission") or []} or None,
            "wishlist_raw": raw_text,                        # whole notes used as wishlist surrogate
            "bio_raw": None,
            "hard_nos_raw": _join_hard_nos(hard_nos),
            "closed_to": [],
            "closed_to_raw": None,
            "response_time": None,
            "profile_notes": parsed,
            "profile_notes_raw": raw_text,
            "prompt_version": PROMPT_VERSION,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate(text: str, max_words: int = 4000) -> str:
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words])

    @staticmethod
    def _extract_section(
        text: str,
        agent_name: str,
        section_hint: str | None = None,
        all_names: list[str] | None = None,
    ) -> str:
        text_lower = text.lower()
        name_lower = agent_name.lower()
        start = text_lower.find(name_lower)
        if start == -1:
            parts = agent_name.split()
            if parts:
                start = text_lower.find(parts[-1].lower())
        if start == -1 and section_hint:
            start = text_lower.find(section_hint.lower().strip())
        if start == -1:
            return text
        end = len(text)
        if all_names:
            for other in all_names:
                if other.lower() == name_lower:
                    continue
                pos = text_lower.find(other.lower(), start + len(agent_name))
                if pos != -1 and pos < end:
                    end = pos
        return text[start:end].strip()

    @staticmethod
    def _upsert_agency(db: Session, source_url: str, agency_info: dict) -> Agency:
        from urllib.parse import urlparse
        name = agency_info["name"].strip()
        domain = urlparse(source_url).netloc.lower()
        existing = db.query(Agency).filter_by(name=name).first() or db.query(Agency).filter_by(domain=domain).first()
        fields = {
            "name": name, "domain": domain,
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
        agency = Agency(**fields)
        db.add(agency)
        db.commit()
        db.refresh(agency)
        return agency

    @staticmethod
    def _pick_richer_list(old, new):
        old, new = old or [], new or []
        return new if len(new) >= len(old) else old

    @staticmethod
    def _pick_non_null(old, new):
        return new if new is not None else old

    @staticmethod
    def _upsert_agent(
        db: Session,
        source_url: str,
        fields: dict,
        quality_score: float,
        quality_action: str,
        review_status: str,
        agency_id: int | None = None,
    ) -> Agent:
        existing = db.query(Agent).filter_by(profile_url=source_url).first()
        name = fields.get("name", "")
        matched_by_name = False
        if not existing and name and name != "(extraction failed)":
            existing = (
                db.query(Agent)
                .filter(
                    func.lower(Agent.name) == name.lower(),
                    func.lower(Agent.agency) == (fields.get("agency") or "").lower(),
                )
                .first()
            )
            if not existing and agency_id is not None:
                existing = (
                    db.query(Agent)
                    .filter(
                        func.lower(Agent.name) == name.lower(),
                        Agent.agency_id == agency_id,
                    )
                    .first()
                )
            matched_by_name = existing is not None

        row = {
            **fields,
            "agency_id": agency_id,
            "quality_score": quality_score,
            "quality_action": quality_action,
            "review_status": review_status,
            "last_crawled_at": datetime.now(timezone.utc),
        }

        if existing and matched_by_name:
            for list_key in ("genres", "genres_raw", "keywords", "audience", "hard_nos_keywords", "closed_to"):
                row[list_key] = ProfileExtractor._pick_richer_list(getattr(existing, list_key, None), row[list_key])
            for scalar_key in ("wishlist_raw", "bio_raw", "hard_nos_raw", "email",
                               "response_time", "submission_req", "agency",
                               "profile_notes", "profile_notes_raw", "prompt_version"):
                row[scalar_key] = ProfileExtractor._pick_non_null(getattr(existing, scalar_key, None), row.get(scalar_key))
            row["is_open"] = ProfileExtractor._pick_non_null(existing.is_open, row.get("is_open"))
            new_richness = len(row.get("genres_raw") or []) + len(row.get("keywords") or [])
            old_richness = len(existing.genres_raw or []) + len(existing.keywords or [])
            if new_richness >= old_richness:
                existing.profile_url = source_url
            for k, v in row.items():
                setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        if existing:
            for k, v in row.items():
                setattr(existing, k, v)
            db.commit()
            db.refresh(existing)
            return existing
        agent = Agent(profile_url=source_url, **row)
        db.add(agent)
        db.commit()
        db.refresh(agent)
        return agent


def _join_hard_nos(hard_nos: dict) -> str | None:
    parts: list[str] = []
    for bucket in ("content", "format", "trope", "category"):
        items = hard_nos.get(bucket) or []
        if items:
            parts.append(f"{bucket.title()}: " + "; ".join(items))
    return "\n".join(parts) if parts else None
