"""
Data layer operations for the review interface.
Separated from Streamlit UI for testability.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from autoquery.database.models import (
    Agent,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_REJECTED,
)

_BLACKLIST_PATH = Path(__file__).parent.parent.parent / "config" / "blacklist.yaml"
_SEED_LIST_PATH = Path(__file__).parent.parent.parent / "config" / "seed_list.yaml"


def _load_blacklist() -> set[str]:
    try:
        with _BLACKLIST_PATH.open() as f:
            data = yaml.safe_load(f)
        return {d.lower() for d in (data.get("domains") or [])}
    except Exception:
        return set()


def approve_agent(db: Session, agent_id: int, reviewed_by: str = "admin") -> Agent | None:
    """Set agent status to approved with review metadata."""
    agent = db.get(Agent, agent_id)
    if not agent:
        return None
    agent.review_status = REVIEW_STATUS_APPROVED
    agent.reviewed_by = reviewed_by
    agent.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)
    return agent


def reject_agent(db: Session, agent_id: int, reason: str, reviewed_by: str = "admin") -> Agent | None:
    """Set agent status to rejected. Reason is required."""
    if not reason or not reason.strip():
        raise ValueError("Rejection reason is required")
    agent = db.get(Agent, agent_id)
    if not agent:
        return None
    agent.review_status = REVIEW_STATUS_REJECTED
    agent.rejection_reason = reason.strip()
    agent.reviewed_by = reviewed_by
    agent.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)
    return agent


def validate_domain(domain: str) -> str | None:
    """Validate a domain string. Returns error message or None if valid."""
    if not domain or not domain.strip():
        return "Domain is empty"
    domain = domain.strip().lower()
    if "." not in domain:
        return f"Invalid domain format: '{domain}' (no TLD)"
    if " " in domain:
        return f"Domain contains spaces: '{domain}'"
    blacklist = _load_blacklist()
    if domain in blacklist:
        return f"Domain '{domain}' is on the blacklist"
    return None


def parse_csv_domains(csv_content: str) -> list[dict]:
    """
    Parse CSV with columns: domain, agency_name, country.
    Returns list of dicts with optional 'error' key for invalid rows.
    """
    reader = csv.DictReader(io.StringIO(csv_content))
    results: list[dict] = []
    for row in reader:
        domain = (row.get("domain") or "").strip()
        agency_name = (row.get("agency_name") or "").strip()
        country = (row.get("country") or "").strip()

        error = validate_domain(domain)
        entry = {"domain": domain, "agency_name": agency_name, "country": country}
        if error:
            entry["error"] = error
        results.append(entry)
    return results


def add_domains_to_seed_list(
    domains: list[dict], seed_path: str | None = None
) -> int:
    """
    Add validated domains to seed_list.yaml, deduplicating by domain name.
    Returns count of newly added domains.
    """
    path = Path(seed_path) if seed_path else _SEED_LIST_PATH
    try:
        with path.open() as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        data = {}

    existing = data.get("domains") or []
    existing_set = {d["domain"] for d in existing if isinstance(d, dict)}
    added = 0

    for entry in domains:
        if entry.get("error"):
            continue
        if entry["domain"] not in existing_set:
            existing.append({
                "domain": entry["domain"],
                "agency_name": entry.get("agency_name", ""),
                "country": entry.get("country", ""),
            })
            existing_set.add(entry["domain"])
            added += 1

    data["domains"] = existing
    with path.open("w") as f:
        yaml.dump(data, f, default_flow_style=False)

    return added
