#!/usr/bin/env python3
"""One-shot filter: Thema v1.6 JSON → canon/thema_{subjects,audience,form}.yaml.

Kept under canon/_source/ for audit trail. Not part of the runtime path.
Rerun only when bumping to a new Thema version.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

HERE = Path(__file__).parent
CANON = HERE.parent
SRC = HERE / "thema_v1.6_en.json"

SUBJECT_ROOTS = ("F", "Y")
SUBJECT_EXTRA_PREFIXES = ("DC", "DD", "DN")  # poetry, plays, biography/memoir/essays
AUDIENCE_PREFIX = "5A"
FORM_PREFIX = "X"


def entry(c: dict) -> dict:
    out = {
        "name": c["CodeDescription"],
        "parent": c["CodeParent"] or None,
    }
    notes = c.get("CodeNotes")
    if notes:
        out["notes"] = notes
    return out


def filter_codes(codes: list[dict]) -> tuple[dict, dict, dict]:
    subjects, audience, form = {}, {}, {}
    for c in codes:
        code = c["CodeValue"]
        if code.startswith(SUBJECT_ROOTS) or code.startswith(SUBJECT_EXTRA_PREFIXES):
            subjects[code] = entry(c)
        elif code.startswith(AUDIENCE_PREFIX):
            audience[code] = entry(c)
        elif code.startswith(FORM_PREFIX):
            form[code] = entry(c)
    return subjects, audience, form


def dump(path: Path, header: str, data: dict) -> None:
    path.write_text(
        f"# {header}\n"
        f"# Source: EDItEUR Thema v1.6 (2025-04-10 English release).\n"
        f"# Do not edit by hand — regenerate via canon/_source/filter_thema.py.\n"
        f"# Local (non-Thema) additions live in canon/extensions.yaml.\n\n"
        + yaml.safe_dump({"codes": data}, sort_keys=True, allow_unicode=True, width=120)
    )


def main() -> None:
    raw = json.loads(SRC.read_text())
    codes = raw["CodeList"]["ThemaCodes"]["Code"]
    subjects, audience, form = filter_codes(codes)

    dump(CANON / "thema_subjects.yaml", "Thema subject codes (fiction + children + memoir/poetry/plays)", subjects)
    dump(CANON / "thema_audience.yaml", "Thema 5A* audience qualifiers (interest age)", audience)
    dump(CANON / "thema_form.yaml", "Thema X* form qualifiers (graphic novels / comics / manga)", form)

    print(f"subjects: {len(subjects)}  audience: {len(audience)}  form: {len(form)}")


if __name__ == "__main__":
    main()
