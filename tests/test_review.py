"""
Tests for review data layer operations (not Streamlit UI).
"""
import csv
import io
import os
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from autoquery.database.models import Agent, REVIEW_STATUS_PENDING, REVIEW_STATUS_APPROVED, REVIEW_STATUS_REJECTED
from autoquery.review.operations import (
    approve_agent,
    reject_agent,
    parse_csv_domains,
    validate_domain,
    add_domains_to_seed_list,
)


@pytest.fixture
def pending_agent(db_session):
    agent = Agent(
        name="Test Agent",
        profile_url="https://example.com/test-agent",
        review_status=REVIEW_STATUS_PENDING,
        genres=["literary_fiction"],
        keywords=["diverse voices", "found family", "atmospheric"],
    )
    db_session.add(agent)
    db_session.commit()
    db_session.refresh(agent)
    return agent


class TestApproveAgent:
    def test_approve_sets_status_and_metadata(self, db_session, pending_agent):
        result = approve_agent(db_session, pending_agent.id, reviewed_by="admin")
        assert result.review_status == REVIEW_STATUS_APPROVED
        assert result.reviewed_by == "admin"
        assert result.reviewed_at is not None

    def test_approve_nonexistent_returns_none(self, db_session):
        result = approve_agent(db_session, 99999, reviewed_by="admin")
        assert result is None


class TestRejectAgent:
    def test_reject_requires_reason(self, db_session, pending_agent):
        result = reject_agent(db_session, pending_agent.id, reason="Bad data", reviewed_by="admin")
        assert result.review_status == REVIEW_STATUS_REJECTED
        assert result.rejection_reason == "Bad data"
        assert result.reviewed_by == "admin"
        assert result.reviewed_at is not None

    def test_reject_empty_reason_raises(self, db_session, pending_agent):
        with pytest.raises(ValueError, match="reason"):
            reject_agent(db_session, pending_agent.id, reason="", reviewed_by="admin")


class TestCSVParsing:
    def test_valid_csv(self):
        csv_content = "domain,agency_name,country\nexample.com,Example Agency,US\ntest.co.uk,Test Lit,UK\n"
        results = parse_csv_domains(csv_content)
        assert len(results) == 2
        assert results[0]["domain"] == "example.com"
        assert results[0]["agency_name"] == "Example Agency"
        assert results[1]["country"] == "UK"

    def test_csv_with_validation_errors(self):
        csv_content = "domain,agency_name,country\n,Missing Domain,US\nexample.com,Good Agency,US\n"
        results = parse_csv_domains(csv_content)
        assert len(results) == 2
        assert results[0].get("error") is not None
        assert results[1].get("error") is None


class TestDomainValidation:
    def test_valid_domain(self):
        assert validate_domain("example.com") is None

    def test_invalid_domain_no_dot(self):
        error = validate_domain("nodot")
        assert error is not None

    def test_blacklisted_domain(self):
        error = validate_domain("querytracker.net")
        assert error is not None
        assert "blacklist" in error.lower()


class TestSeedListWrite:
    def test_add_domains_to_seed_list(self, tmp_path):
        seed_file = tmp_path / "seed_list.yaml"
        seed_file.write_text("domains: []\n")

        domains = [
            {"domain": "example.com", "agency_name": "Example", "country": "US"},
            {"domain": "test.co.uk", "agency_name": "Test", "country": "UK"},
        ]

        add_domains_to_seed_list(domains, seed_path=str(seed_file))

        data = yaml.safe_load(seed_file.read_text())
        assert len(data["domains"]) == 2
        assert data["domains"][0]["domain"] == "example.com"

    def test_add_domains_deduplicates(self, tmp_path):
        seed_file = tmp_path / "seed_list.yaml"
        seed_file.write_text(yaml.dump({"domains": [{"domain": "example.com", "agency_name": "Old", "country": "US"}]}))

        domains = [
            {"domain": "example.com", "agency_name": "New", "country": "US"},
            {"domain": "new.com", "agency_name": "New Agency", "country": "US"},
        ]

        add_domains_to_seed_list(domains, seed_path=str(seed_file))

        data = yaml.safe_load(seed_file.read_text())
        assert len(data["domains"]) == 2
        # Existing entry should not be duplicated
        example_entries = [d for d in data["domains"] if d["domain"] == "example.com"]
        assert len(example_entries) == 1
