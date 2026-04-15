"""Parse Note-Taker (prompt v2.0) plain-text output into a structured dict.

The L1 Note-Taker prompt produces a deterministic 8-step layout
(STEP 1 IDENTITY … STEP 8 CONFIDENCE FLAGS). This parser is intentionally
tolerant: missing sections, extra whitespace, missing fields all return
``None`` / ``[]`` rather than raise. Hard requirements live downstream.
"""
from __future__ import annotations

import re
from typing import Any

_STEP_RE = re.compile(r"^STEP\s+(\d+)\s*[:\-]\s*(.+?)\s*$", re.IGNORECASE)
_BULLET_RE = re.compile(r"^[\-\*•]\s+(.*\S)\s*$")
_FIELD_RE = re.compile(r"^([A-Za-z][A-Za-z /&'-]*?)\s*:\s*(.*)$")
_SECTION_LABEL_RE = re.compile(r"^\[([^\]]+)\]\s*$")
_MD_HEADER_PREFIX_RE = re.compile(r"^#{1,6}\s*")
_MD_BOLD_WRAPPER_RE = re.compile(r"\*\*([^*]+?)\*\*")


def _strip_markdown(line: str) -> str:
    """Remove leading Markdown header hashes and unwrap **bold** emphasis.

    Some LLMs (notably Sonnet variants) format Note-Taker output with Markdown
    wrappers — ``## STEP 1: IDENTITY``, ``**Name:** Foo``, ``### [LABEL]``.
    The parser's line regexes expect plain text, so we normalize first.
    """
    s = _MD_HEADER_PREFIX_RE.sub("", line)
    s = _MD_BOLD_WRAPPER_RE.sub(r"\1", s)
    return s
_STRENGTH_RE = re.compile(
    r"^(REQUIRED|STRONGLY PREFERRED|PREFERRED)\b[\s\-—:]*(.+)$",
    re.IGNORECASE,
)

_AUDIENCE_TOKENS = {
    "picture_books", "middle_grade", "young_adult", "new_adult",
    "adult", "all_ages", "crossover",
}


def parse(raw: str) -> dict[str, Any]:
    """Parse Note-Taker output text into a structured dict.

    The returned dict always has all top-level keys; absent sections
    yield empty containers, not missing keys.
    """
    sections = _split_into_steps(raw)

    return {
        "identity": _parse_identity(sections.get(1, "")),
        "global_conditions": _parse_global_conditions(sections.get(2, "")),
        "preference_sections": _parse_preference_sections(sections.get(3, "")),
        "hard_nos": _parse_hard_nos(sections.get(4, "")),
        "submission": _parse_submission(sections.get(5, "")),
        "comp_titles_high_priority": _parse_comps_high_priority(sections.get(6, "")),
        "taste_references": _parse_taste_references(sections.get(6, "")),
        "cross_cutting_themes": _parse_bullets(sections.get(7, "")),
        "confidence_flags": _parse_confidence_flags(sections.get(8, "")),
    }


def _split_into_steps(raw: str) -> dict[int, str]:
    """Split text into a dict keyed by STEP number, value = body text."""
    out: dict[int, str] = {}
    current_step: int | None = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        normalized = _strip_markdown(line.strip())
        m = _STEP_RE.match(normalized)
        if m:
            if current_step is not None:
                out[current_step] = "\n".join(current_lines).strip()
            current_step = int(m.group(1))
            current_lines = []
        else:
            if current_step is not None:
                current_lines.append(_strip_markdown(line))
    if current_step is not None:
        out[current_step] = "\n".join(current_lines).strip()
    return out


def _iter_field_lines(body: str):
    """Yield (key_lower, value) pairs from `Field: value` lines."""
    for line in body.splitlines():
        s = line.strip()
        if not s or s.startswith(("-", "*", "•", "[", "===", "---")):
            continue
        m = _FIELD_RE.match(s)
        if m:
            yield m.group(1).strip().lower(), m.group(2).strip()


def _clean_value(v: str) -> str | None:
    if v is None:
        return None
    v = v.strip().strip("—–-").strip()
    if not v:
        return None
    if v.lower() in {"none", "null", "n/a", "(not listed)", "not listed"}:
        return None
    return v


def _parse_identity(body: str) -> dict[str, Any]:
    out: dict[str, Any] = {
        "name": None, "organization": None, "role": None, "pronouns": None,
        "email": None, "submission_portal": None, "availability": None,
        "availability_note": None,
    }
    for key, val in _iter_field_lines(body):
        cleaned = _clean_value(val)
        if key == "name":
            out["name"] = cleaned
        elif key == "organization":
            out["organization"] = cleaned
        elif key == "role":
            out["role"] = cleaned
        elif key == "pronouns":
            out["pronouns"] = cleaned
        elif key == "email":
            out["email"] = cleaned
        elif key == "submission portal":
            out["submission_portal"] = cleaned
        elif key == "availability":
            if cleaned:
                first = cleaned.split()[0].upper().rstrip(",.")
                out["availability"] = first if first in {"OPEN", "CLOSED", "CONDITIONAL"} else cleaned
                if " " in cleaned:
                    out["availability_note"] = cleaned.split(" ", 1)[1].strip(" ,—-")
    return out


def _parse_global_conditions(body: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for line in body.splitlines():
        m = _BULLET_RE.match(line.strip())
        if not m:
            continue
        text = m.group(1)
        # Try to detect strength tag (e.g. "... → REQUIRED" or "REQUIRED — ...")
        strength = None
        arrow_match = re.search(r"(?:→|->|=>)\s*(REQUIRED|STRONGLY PREFERRED|PREFERRED)\b", text, re.IGNORECASE)
        if arrow_match:
            strength = arrow_match.group(1).upper().replace(" ", "_")
            text = text[:arrow_match.start()].strip(" —-:")
        else:
            sm = _STRENGTH_RE.match(text)
            if sm:
                strength = sm.group(1).upper().replace(" ", "_")
                text = sm.group(2).strip(" —-:")
        out.append({"text": text, "strength": strength})
    return out


# Sub-fields recognised inside a preference section
_PREF_LIST_FIELDS = {
    "audience": "audience",
    "genres": "genres",
    "wants": "wants",
    "conditions": "conditions",
    "does not want": "does_not_want",
    "tropes wanted": "tropes_wanted",
    "tropes excluded": "tropes_excluded",
    "comp titles": "comp_titles",
}


def _parse_preference_sections(body: str) -> list[dict[str, Any]]:
    """Walk the body, splitting on `[SECTION LABEL]` markers."""
    sections: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    current_field: str | None = None

    for line in body.splitlines():
        s_strip = line.strip()
        if not s_strip:
            current_field = None
            continue

        m_label = _SECTION_LABEL_RE.match(s_strip)
        if m_label:
            if current is not None:
                sections.append(_finalize_section(current))
            current = {
                "label": m_label.group(1).strip(),
                "audience": [], "genres": [],
                "wants": [], "conditions": [], "does_not_want": [],
                "tropes_wanted": [], "tropes_excluded": [],
                "comp_titles": [],
            }
            current_field = None
            continue

        if current is None:
            continue

        # Field header line, e.g. "Wants:"
        m_field = _FIELD_RE.match(s_strip)
        if m_field:
            key_lower = m_field.group(1).strip().lower()
            if key_lower in _PREF_LIST_FIELDS:
                current_field = _PREF_LIST_FIELDS[key_lower]
                rest = m_field.group(2).strip()
                if rest:
                    _append_to_field(current, current_field, rest)
                continue

        # Bullet line under current field
        m_bullet = _BULLET_RE.match(s_strip)
        if m_bullet and current_field:
            _append_to_field(current, current_field, m_bullet.group(1))
            continue

    if current is not None:
        sections.append(_finalize_section(current))
    return sections


def _append_to_field(section: dict[str, Any], field: str, value: str) -> None:
    value = value.strip()
    if not value:
        return
    if field == "comp_titles":
        section["comp_titles"].append(_parse_comp_entry(value))
    elif field == "audience":
        for tok in re.split(r"[,;|/]+", value):
            t = tok.strip().lower().replace(" ", "_").replace("-", "_")
            if t in _AUDIENCE_TOKENS:
                section["audience"].append(t)
    elif field == "genres":
        for tok in re.split(r"[,;|]+", value):
            t = tok.strip()
            if t:
                section["genres"].append(t)
    else:
        section[field].append(value)


def _finalize_section(section: dict[str, Any]) -> dict[str, Any]:
    # Dedupe audience, preserve order
    seen: set[str] = set()
    section["audience"] = [a for a in section["audience"] if not (a in seen or seen.add(a))]
    return section


_COMP_RE = re.compile(
    r"^(?P<title>.+?)\s+by\s+(?P<author>.+?)(?:\s*[—\-→]\s*(?P<note>.+))?$",
    re.IGNORECASE,
)


def _parse_comp_entry(text: str) -> dict[str, str | None]:
    text = text.strip().strip("[]")
    m = _COMP_RE.match(text)
    if m:
        return {
            "title": m.group("title").strip(),
            "author": m.group("author").strip(),
            "illustrates": (m.group("note") or "").strip() or None,
        }
    # No "by author" — split on arrow/dash for note
    if "→" in text or " — " in text or " - " in text:
        for sep in ("→", " — ", " - "):
            if sep in text:
                head, tail = text.split(sep, 1)
                return {"title": head.strip(), "author": None, "illustrates": tail.strip() or None}
    return {"title": text, "author": None, "illustrates": None}


def _parse_hard_nos(body: str) -> dict[str, list[str]]:
    out = {"content": [], "format": [], "trope": [], "category": []}
    current: str | None = None

    field_map = {
        "content nos": "content", "format nos": "format",
        "trope nos": "trope", "category nos": "category",
    }
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        m_field = _FIELD_RE.match(s)
        if m_field:
            key = m_field.group(1).strip().lower()
            if key in field_map:
                current = field_map[key]
                rest = m_field.group(2).strip()
                if rest:
                    _split_hard_no_into(out[current], rest)
                continue
        m_bullet = _BULLET_RE.match(s)
        if m_bullet and current:
            _split_hard_no_into(out[current], m_bullet.group(1))
    return out


def _split_hard_no_into(target: list[str], text: str) -> None:
    """A hard-no value may be one phrase or comma-separated phrases."""
    text = text.strip().strip("()").strip()
    if not text:
        return
    # If it contains parenthetical examples, keep the whole thing as one entry
    if "(" in text and ")" in text:
        target.append(text)
        return
    for tok in re.split(r"\s*[,;]\s*", text):
        t = tok.strip()
        if t:
            target.append(t)


def _parse_submission(body: str) -> list[dict[str, Any]]:
    """Each submission block: optional category header, then Submit via / Materials / Special notes."""
    blocks: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    field_map = {
        "submit via": "submit_via",
        "materials": "materials",
        "special notes": "special_notes",
    }

    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue

        # Bare bullet at top level → "Also note" items
        m_bullet = _BULLET_RE.match(s)
        if m_bullet and (current is None or all(v is None for v in current.values() if not isinstance(v, str))):
            if current is None:
                current = {"category": None, "submit_via": None, "materials": None, "special_notes": None, "notes": []}
            current.setdefault("notes", []).append(m_bullet.group(1))
            continue

        m_field = _FIELD_RE.match(s)
        if m_field:
            key_lower = m_field.group(1).strip().lower()
            val = m_field.group(2).strip()
            if key_lower in field_map:
                if current is None:
                    current = {"category": None, "submit_via": None, "materials": None, "special_notes": None}
                current[field_map[key_lower]] = _clean_value(val)
                continue
            if key_lower == "per category or format":
                continue
            # Heading like "Picture Books:" → start new block
            if current is not None and any(current.get(k) for k in field_map.values()):
                blocks.append(current)
            current = {
                "category": m_field.group(1).strip(),
                "submit_via": None, "materials": _clean_value(val) or None, "special_notes": None,
            }
            continue

    if current is not None:
        blocks.append(current)
    return blocks


def _parse_comps_high_priority(body: str) -> list[dict[str, str | None]]:
    """Section 6A — comps under a HIGH-PRIORITY heading."""
    out: list[dict[str, str | None]] = []
    in_section = False
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^A\)\s*HIGH[- ]PRIORITY", s, re.IGNORECASE):
            in_section = True
            continue
        if re.match(r"^B\)\s*TASTE", s, re.IGNORECASE):
            in_section = False
            continue
        if in_section:
            m = _BULLET_RE.match(s)
            if m:
                out.append(_parse_comp_entry(m.group(1)))
    return out


def _parse_taste_references(body: str) -> dict[str, list[str]]:
    out = {"books": [], "film_tv": [], "music": []}
    in_b_section = False
    current: str | None = None
    field_map = {"books": "books", "film/tv": "film_tv", "film & tv": "film_tv", "music": "music"}

    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^B\)\s*TASTE", s, re.IGNORECASE):
            in_b_section = True
            continue
        if not in_b_section:
            continue
        m_field = _FIELD_RE.match(s)
        if m_field:
            key = m_field.group(1).strip().lower()
            if key in field_map:
                current = field_map[key]
                rest = m_field.group(2).strip()
                if rest:
                    out[current].extend([t.strip() for t in re.split(r"[,;]+", rest) if t.strip()])
                continue
        m_bullet = _BULLET_RE.match(s)
        if m_bullet and current:
            out[current].append(m_bullet.group(1))
    return out


def _parse_bullets(body: str) -> list[str]:
    out: list[str] = []
    for line in body.splitlines():
        m = _BULLET_RE.match(line.strip())
        if m:
            out.append(m.group(1))
    return out


def _parse_confidence_flags(body: str) -> dict[str, list[str]]:
    out = {"inferred": [], "nuanced": [], "missing": []}
    current: str | None = None
    keymap = {"inferred": "inferred", "nuanced": "nuanced", "missing": "missing"}

    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        first = s.split()[0].upper().rstrip(":-—")
        if first.lower() in keymap:
            current = keymap[first.lower()]
            rest = s.split(None, 1)[1] if " " in s else ""
            rest = rest.strip(" —-:")
            if rest:
                out[current].append(rest)
            continue
        m_bullet = _BULLET_RE.match(s)
        if m_bullet and current:
            out[current].append(m_bullet.group(1))
    return out
